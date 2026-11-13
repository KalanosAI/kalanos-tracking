"""Load a snapshot through Kalanos; export an explicit, small allowlist."""
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
import json
import math
import tempfile
from typing import Any


def _get(obj: Any, path: str, default=None):
    for key in path.split('.'):
        obj = getattr(obj, key, default)
        if obj is default:
            break
    return obj.value if isinstance(obj, Enum) else obj


@dataclass(frozen=True)
class Assessment:
    """Immutable report bytes. Exposing raw bytes is an explicit caller action."""
    raw: bytes
    summary_json: str

    @property
    def summary(self) -> dict:
        return json.loads(self.summary_json)

    @property
    def sha256(self) -> str:
        return sha256(self.raw).hexdigest()


def _summarize(report, raw: bytes) -> Assessment:
    schema = _get(report, 'schema_version')
    if schema not in {'7.0.0', '7.1.0', '7.2.0', '7.3.0', '8.0.0'}:
        raise ValueError('Unsupported report schema; do not map legacy readiness.')
    metrics = {}
    fields = {
        'readiness_score': 'readiness.score',
        'descriptive_score': 'score.score',
        'episodes_total': 'eligibility_counts.total',
        'episodes_pass': 'eligibility_counts.pass_count',
        'episodes_review': 'eligibility_counts.review',
        'episodes_blocked': 'eligibility_counts.blocked',
        'episodes_unknown': 'eligibility_counts.unknown',
        'confirmed_eligible_share': 'eligibility_counts.confirmed_eligible_share',
    }
    for name, field in fields.items():
        value = _get(report, field)
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'Invalid numeric field: {name}')
            metrics[name] = value
    metadata = {'schema_version': schema, 'report_sha256': sha256(raw).hexdigest(),
                'readiness_defined': _get(report, 'readiness.score') is not None}
    for name, field in {
        'producer_version': 'producer.version', 'run_id': 'run.id',
        'completion': 'run.completion', 'tier': 'scope.tier',
        'source_revision': 'run.source.revision', 'source_digest': 'run.source.digest',
        'source_scope': 'run.source.scope', 'source_complete': 'run.source.complete',
        'requirements_id': 'scope.requirements_id', 'policy_id': 'scope.policy_id',
        'binding_id': 'scope.binding_id', 'readiness_formula': 'readiness.formula_id',
        'sufficiency_status': 'sufficiency.status',
        'inventory_complete': 'eligibility_counts.inventory_complete',
    }.items():
        value = _get(report, field)
        if isinstance(value, (str, bool, int)):
            metadata[name] = value
    # Do not export arbitrary reason text, source paths, tasks or evidence.
    # Missing coverage stays missing, not zero. Use only structured counts.
    coverage = _get(report, 'coverage')
    metadata['coverage_recorded'] = coverage is not None
    rows = []
    if coverage is not None:
        for family in ('metrics', 'capabilities', 'dimensions'):
            for row in getattr(coverage, family, []):
                item = {'group': family, 'key': row.key, 'unit': row.unit}
                for name in ('computed', 'eligible', 'not_applicable', 'unavailable', 'skipped', 'error', 'not_required'):
                    value = getattr(row, name, None)
                    if isinstance(value, int) and not isinstance(value, bool):
                        item[name] = value
                rows.append(item)
    summary = {'format': 'kalanos-tracking-summary-v1', 'metrics': metrics,
               'metadata': metadata, 'coverage': rows}
    return Assessment(raw, json.dumps(summary, sort_keys=True, allow_nan=False))


def load_assessment(path: str | Path, *, max_bytes: int = 256 * 1024 * 1024) -> Assessment:
    """Read local JSON once; Kalanos validates and decodes compact/reason tables.

    No URLs, grading, downloads, credentials or external calls. The byte cap is
    an input-size limit, not a bound on the parsed model's memory usage.
    """
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError('max_bytes must be a positive integer')
    from kalanos import load_report
    from kalanos.analysis.models.report import Report
    with Path(path).open('rb') as handle:
        raw = handle.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError('Report exceeds max_bytes')
    with tempfile.TemporaryDirectory(prefix='kalanos-tracking-') as directory:
        snapshot = Path(directory) / 'audit.json'
        snapshot.write_bytes(raw)
        report = load_report(snapshot)
        if not isinstance(report, Report):
            raise ValueError('Legacy reports cannot supply current decisions; regrade first')
    return _summarize(report, raw)
