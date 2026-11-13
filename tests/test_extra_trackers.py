from pathlib import Path
import tempfile
from types import SimpleNamespace as N
from unittest.mock import patch
import unittest
from test_tracking import fixture
from kalanos_tracking import log_to_tensorboard, log_to_trackio

class Writer:
    def __init__(self): self.scalars=[]; self.text=[]
    def add_scalar(self,*a,**kw): self.scalars.append((a,kw))
    def add_text(self,*a,**kw): self.text.append((a,kw))
    def close(self): raise AssertionError('Caller owns lifecycle')

class Run:
    def __init__(self): self.entries=[]; self.artifacts=[]
    def log(self,*a,**kw): self.entries.append((a,kw))
    def log_artifact(self,path,**kw):
        self.artifacts.append({p.name:p.read_bytes() for p in Path(path).iterdir()})

class ExtraTests(unittest.TestCase):
    def test_tensorboard(self):
        w=Writer(); result=log_to_tensorboard(fixture(),writer=w,step=12)
        self.assertEqual(result.status,'logged'); self.assertTrue(w.scalars)
        self.assertEqual(w.text[0][1]['global_step'],12)
    def test_tensorboard_requires_sidecar_dir(self):
        with self.assertRaises(ValueError): log_to_tensorboard(fixture(),writer=Writer(),artifact='full')
    def test_tensorboard_sidecars(self):
        a=fixture()
        with tempfile.TemporaryDirectory() as d:
            log_to_tensorboard(a,writer=Writer(),artifact='full',report_dir=d)
            self.assertEqual((Path(d)/'dataset'/a.sha256/'audit.json').read_bytes(),a.raw)
    def test_tensorboard_invalid_step(self):
        with self.assertRaises(ValueError): log_to_tensorboard(fixture(),writer=Writer(),step=-1)
    def test_tensorboard_failure(self):
        w=Writer(); w.add_scalar=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError())
        self.assertEqual(log_to_tensorboard(fixture(),writer=w).status,'error')
    def test_trackio_history(self):
        r=Run()
        with patch.dict('sys.modules',{'trackio':N(Markdown=lambda x: x)}):
            result=log_to_trackio(fixture(),run=r,step=7)
        self.assertEqual(result.status,'logged'); self.assertEqual(r.entries[0][1]['step'],7)
        self.assertFalse(r.artifacts)
    def test_trackio_artifact(self):
        r=Run()
        with patch.dict('sys.modules',{'trackio':N(Markdown=lambda x: x)}):
            log_to_trackio(fixture(),run=r,step=0,artifact='summary')
        self.assertEqual(set(r.artifacts[0]),{'summary.json'})
    def test_trackio_invalid_step(self):
        with self.assertRaises(ValueError): log_to_trackio(fixture(),run=Run(),step=True)
    def test_trackio_failure(self):
        r=Run(); r.log=lambda *a,**kw: (_ for _ in ()).throw(RuntimeError())
        with patch.dict('sys.modules',{'trackio':N(Markdown=lambda x: x)}):
            self.assertEqual(log_to_trackio(fixture(),run=r,step=0).status,'error')
