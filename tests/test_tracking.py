import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

from kalanos_tracking import Assessment, log_to_wandb, log_to_mlflow
from kalanos_tracking.report import _summarize


def fixture(**changes):
    r = N(schema_version='8.0.0', score=N(score=98.5),
          readiness=N(score=None, formula_id='v1', reasons=['private path /secret']),
          eligibility_counts=N(total=3, pass_count=1, review=1, blocked=0,
                               unknown=1, inventory_complete=True, confirmed_eligible_share=1/3),
          producer=N(version='0.9.3'), run=N(id='test', completion='complete',
          source=N(revision='abc', digest='def', scope='metadata', complete=True)),
          scope=N(tier='standard', requirements_id='numeric-core-v1', policy_id='default'),
          sufficiency=N(status='unknown'), coverage=None,
          source_paths=['/secret'], tasks=['private task'], evidence={'token':'SECRET'})
    for k,v in changes.items(): setattr(r,k,v)
    return _summarize(r, b'{"private":"original"}')

class Run:
    def __init__(self): self.summary={}; self.artifacts=[]
    def log_artifact(self,a): self.artifacts.append(a)
    def log(self,*a,**kw): raise AssertionError('Do not alter training steps')
    def finish(self): raise AssertionError('Caller owns run')

class Client:
    def __init__(self): self.tags={}; self.metrics=[]; self.files=[]
    def get_run(self,id): return N(data=N(tags=self.tags))
    def set_tag(self,id,k,v): self.tags[k]=v
    def log_metric(self,id,k,v): self.metrics.append((k,v))
    def log_artifact(self,id,path,artifact_path): self.files.append((Path(path).name,Path(path).read_bytes()))

class Tests(unittest.TestCase):
    def test_undefined_is_not_zero(self):
        a=fixture(); self.assertNotIn('readiness_score',a.summary['metrics'])
        self.assertFalse(a.summary['metadata']['readiness_defined'])
    def test_zero_is_retained(self):
        a=fixture(readiness=N(score=0,formula_id='v1'))
        self.assertEqual(a.summary['metrics']['readiness_score'],0)
    def test_descriptive_is_separate(self): self.assertEqual(fixture().summary['metrics']['descriptive_score'],98.5)
    def test_no_private_text(self):
        s=fixture().summary_json
        for word in ('/secret','private task','SECRET','original','reasons'): self.assertNotIn(word,s)
    def test_snapshot_immutable_view(self):
        a=fixture(); a.summary['metrics'].clear(); self.assertTrue(a.summary['metrics'])
    def test_missing_coverage_not_zero(self): self.assertFalse(fixture().summary['metadata']['coverage_recorded'])
    def test_coverage_counts(self):
        a=fixture(coverage=N(metrics=[N(key='timing',unit='episode',computed=2,eligible=3,skipped=1)]))
        self.assertEqual(a.summary['coverage'][0]['eligible'],3)
    def test_nan_rejected(self):
        with self.assertRaises(ValueError): fixture(score=N(score=float('nan')))
    def test_future_rejected(self):
        with self.assertRaises(ValueError): fixture(schema_version='9.0.0')
    def test_legacy_rejected(self):
        with self.assertRaises(ValueError): fixture(schema_version='6.5.0')
    def test_wandb_no_history(self):
        r=Run(); result=log_to_wandb(fixture(),run=r)
        self.assertEqual(result.status,'logged'); self.assertEqual(r.artifacts,[])
        self.assertIn('kalanos/dataset/episodes_unknown',r.summary)
    def test_wandb_dedupe(self):
        r=Run(); a=fixture(); log_to_wandb(a,run=r)
        self.assertEqual(log_to_wandb(a,run=r).status,'already_logged')
    def test_wandb_conflict(self):
        r=Run(); a=fixture(); log_to_wandb(a,run=r)
        b=Assessment(b'other',a.summary_json)
        with self.assertRaises(ValueError): log_to_wandb(b,run=r)
    def test_separate_slots(self):
        r=Run(); a=fixture(); log_to_wandb(a,run=r,slot='train'); log_to_wandb(a,run=r,slot='eval')
        self.assertIn('kalanos/eval/episodes_total',r.summary)
    def test_invalid_slot(self):
        with self.assertRaises(ValueError): log_to_wandb(fixture(),run=Run(),slot='../bad')
    def test_invalid_artifact(self):
        with self.assertRaises(ValueError): log_to_wandb(fixture(),run=Run(),artifact='everything')
    def test_missing_run(self):
        with self.assertRaises(ValueError): log_to_wandb(fixture(),run=None)
    def test_mlflow_metrics_and_dedupe(self):
        c=Client(); a=fixture(); self.assertEqual(log_to_mlflow(a,run_id='run',client=c).status,'logged')
        n=len(c.metrics); self.assertEqual(log_to_mlflow(a,run_id='run',client=c).status,'already_logged')
        self.assertEqual(len(c.metrics),n); self.assertFalse(c.files)
    def test_mlflow_summary_artifact(self):
        c=Client(); log_to_mlflow(fixture(),run_id='run',client=c,artifact='summary')
        self.assertEqual([x[0] for x in c.files],['summary.json'])
        self.assertNotIn(b'original',c.files[0][1])
    def test_mlflow_full_opt_in(self):
        c=Client(); a=fixture(); log_to_mlflow(a,run_id='run',client=c,artifact='full')
        self.assertEqual(c.files[1],('audit.json',a.raw))
    def test_failure_and_strict(self):
        c=Client(); c.get_run=lambda id: (_ for _ in ()).throw(RuntimeError('secret-token'))
        result=log_to_mlflow(fixture(),run_id='r',client=c)
        self.assertEqual(result.status,'error'); self.assertNotIn('secret',repr(result))
        with self.assertRaises(RuntimeError): log_to_mlflow(fixture(),run_id='r',client=c,strict=True)
    def test_partial_failure_has_no_marker(self):
        c=Client(); c.log_metric=lambda *a: (_ for _ in ()).throw(RuntimeError())
        self.assertEqual(log_to_mlflow(fixture(),run_id='r',client=c).status,'error')
        self.assertNotIn('kalanos/dataset/logging_state',c.tags)
    def test_wandb_summary_artifact(self):
        class Artifact:
            def __init__(self,*a,**kw): self.files=[]
            def add_file(self,path,name): self.files.append((name,Path(path).read_bytes()))
        r=Run()
        with patch.dict(sys.modules,{'wandb':N(Artifact=Artifact)}):
            log_to_wandb(fixture(),run=r,artifact='summary')
        self.assertEqual(r.artifacts[0].files[0][0],'summary.json')
    def test_wandb_marker_read_failure(self):
        class Broken(dict):
            def get(self, key): raise RuntimeError('secret')
        r=Run(); r.summary=Broken()
        result=log_to_wandb(fixture(),run=r)
        self.assertEqual(result.status,'error')
        self.assertNotIn('secret',repr(result))
    def test_malformed_slot_state(self):
        r=Run(); r.summary['kalanos/dataset/logging_state']='[]'
        with self.assertRaises(ValueError): log_to_wandb(fixture(),run=r)
    def test_provenance(self):
        m=fixture().summary['metadata']; self.assertEqual(m['source_revision'],'abc'); self.assertEqual(len(m['report_sha256']),64)

if __name__=='__main__': unittest.main()
