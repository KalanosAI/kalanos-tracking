from pathlib import Path
import tempfile
from types import ModuleType, SimpleNamespace as N
import unittest
from unittest.mock import patch
from kalanos_tracking import load_assessment

class Report:
    schema_version='8.0.0'

class LoaderTests(unittest.TestCase):
    def modules(self, loader):
        k=ModuleType('kalanos'); k.load_report=loader
        r=ModuleType('kalanos.analysis.models.report'); r.Report=Report
        return {'kalanos':k,'kalanos.analysis':ModuleType('kalanos.analysis'),
                'kalanos.analysis.models':ModuleType('kalanos.analysis.models'),
                'kalanos.analysis.models.report':r}
    def test_loads_exact_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'audit.json'; path.write_bytes(b'{}')
            def loader(snapshot):
                self.assertEqual(snapshot.read_bytes(),b'{}')
                path.write_bytes(b'changed')
                return Report()
            with patch.dict('sys.modules',self.modules(loader)):
                a=load_assessment(path)
            self.assertEqual(a.raw,b'{}')
    def test_legacy_loader_return_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'audit.json'; path.write_bytes(b'{}')
            with patch.dict('sys.modules',self.modules(lambda p: N())):
                with self.assertRaises(ValueError): load_assessment(path)
    def test_size_cap(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'audit.json'; path.write_bytes(b'{}')
            with patch.dict('sys.modules',self.modules(lambda p: Report())):
                with self.assertRaises(ValueError): load_assessment(path,max_bytes=1)
    def test_negative_cap_rejected(self):
        with self.assertRaises(ValueError): load_assessment('unused',max_bytes=-1)
    def test_upstream_validation_preserved(self):
        def invalid(p): raise ValueError('bad report')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'audit.json'; path.write_bytes(b'{}')
            with patch.dict('sys.modules',self.modules(invalid)):
                with self.assertRaisesRegex(ValueError,'bad report'): load_assessment(path)
