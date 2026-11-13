"""Caller-owned runs only: never init, finish or authenticate. Steps are backend-specific."""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
from .report import Assessment


@dataclass(frozen=True)
class LoggingResult:
    status: str  # logged | already_logged | error
    report_sha256: str
    error_type: str | None = None


def _validate(assessment, slot, artifact):
    if not isinstance(assessment, Assessment):
        raise TypeError('Use load_assessment() first')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,39}', slot):
        raise ValueError('slot must be a simple 1–40 character name')
    if artifact not in {'none', 'summary', 'full'}:
        raise ValueError('artifact must be none, summary or full')
    return f'kalanos/{slot}'


def _payload(assessment, prefix):
    summary = assessment.summary
    metrics = {f'{prefix}/{k}': v for k, v in summary['metrics'].items()}
    metadata = {f'{prefix}/{k}': str(v).lower() if isinstance(v, bool) else str(v)
                for k, v in summary['metadata'].items()}
    return metrics, metadata


def _state(existing, digest, artifact):
    if existing is None:
        return False
    try:
        state = json.loads(existing)
    except (ValueError, TypeError):
        raise ValueError('Existing Kalanos slot is invalid; choose another slot') from None
    if not isinstance(state, dict):
        raise ValueError('Existing Kalanos slot is invalid; choose another slot')
    if state.get('sha256') != digest:
        raise ValueError('This run slot already contains another report; choose another slot')
    return state.get('artifact') == artifact


def _marker(assessment, artifact):
    return json.dumps({'sha256': assessment.sha256, 'artifact': artifact}, sort_keys=True)


def _files(directory, assessment, artifact):
    summary = Path(directory) / 'summary.json'
    summary.write_text(assessment.summary_json + '\n', encoding='utf-8')
    files = [summary]
    if artifact == 'full':
        report = Path(directory) / 'audit.json'
        report.write_bytes(assessment.raw)
        files.append(report)
    return files


def log_to_wandb(assessment: Assessment, *, run, slot='dataset', artifact='none', strict=False):
    """Write static run summary, not training history. Optional artifact upload.

    artifact='full' explicitly sends original report bytes, which may contain
    private paths, task text and embedded evidence. Summary fields are also
    transmitted to the run's configured destination. Caller finishes the run.
    """
    prefix = _validate(assessment, slot, artifact)
    if run is None:
        raise ValueError('An existing W&B run is required')
    marker = f'{prefix}/logging_state'
    # A different report in a slot is a caller error, never a swallowed outage.
    try:
        existing = run.summary.get(marker)
    except Exception as exc:
        if strict:
            raise
        return LoggingResult('error', assessment.sha256, type(exc).__name__)
    if _state(existing, assessment.sha256, artifact):
        return LoggingResult('already_logged', assessment.sha256)
    try:
        metrics, metadata = _payload(assessment, prefix)
        run.summary.update({**metrics, **metadata})
        if artifact != 'none':
            import wandb
            with tempfile.TemporaryDirectory(prefix='kalanos-tracking-') as directory:
                item = wandb.Artifact(f'kalanos-{slot}-{assessment.sha256[:16]}',
                                      type='dataset-assessment')
                for path in _files(directory, assessment, artifact):
                    item.add_file(str(path), name=path.name)
                run.log_artifact(item)
        run.summary[marker] = _marker(assessment, artifact)
        return LoggingResult('logged', assessment.sha256)
    except Exception as exc:
        if strict:
            raise
        # Do not echo SDK messages which may contain credential-bearing URLs.
        return LoggingResult('error', assessment.sha256, type(exc).__name__)


def log_to_mlflow(assessment: Assessment, *, run_id: str, client=None,
                  slot='dataset', artifact='none', strict=False):
    """Log to an explicit existing MLflow run without changing the active run.

    MLflow metrics use its default step 0; these are assessment metrics, not
    training-history steps. Repeated successful identical calls are skipped.
    """
    prefix = _validate(assessment, slot, artifact)
    if not isinstance(run_id, str) or not run_id:
        raise ValueError('An existing MLflow run_id is required')
    try:
        if client is None:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
        existing = client.get_run(run_id)
    except Exception as exc:
        if strict:
            raise
        return LoggingResult('error', assessment.sha256, type(exc).__name__)
    marker = f'{prefix}/logging_state'
    if _state(existing.data.tags.get(marker), assessment.sha256, artifact):
        return LoggingResult('already_logged', assessment.sha256)
    try:
        metrics, metadata = _payload(assessment, prefix)
        for key, value in metrics.items():
            client.log_metric(run_id, key, value)
        for key, value in metadata.items():
            client.set_tag(run_id, key, value)
        if artifact != 'none':
            with tempfile.TemporaryDirectory(prefix='kalanos-tracking-') as directory:
                for path in _files(directory, assessment, artifact):
                    client.log_artifact(run_id, str(path), artifact_path=f'kalanos/{slot}')
        client.set_tag(run_id, marker, _marker(assessment, artifact))
        return LoggingResult('logged', assessment.sha256)
    except Exception as exc:
        if strict:
            raise
        return LoggingResult('error', assessment.sha256, type(exc).__name__)


def log_to_tensorboard(assessment: Assessment, *, writer, step=0, slot='dataset',
                       artifact='none', report_dir=None, strict=False):
    """Write scalars/text to caller's SummaryWriter; optional local sidecars.

    TensorBoard has no report-artifact registry. A report_dir is required for
    explicit summary/full sidecar export. Call once per assessment; no dedupe.
    This does not close or flush the writer: caller retains its lifecycle.
    """
    prefix = _validate(assessment, slot, artifact)
    if writer is None:
        raise ValueError('An existing TensorBoard SummaryWriter is required')
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError('step must be a nonnegative integer')
    if artifact != 'none' and report_dir is None:
        raise ValueError('TensorBoard sidecars require an explicit report_dir')
    try:
        metrics, _ = _payload(assessment, prefix)
        for key, value in metrics.items():
            writer.add_scalar(key, value, global_step=step)
        writer.add_text(f'{prefix}/assessment',
                        '```json\n' + assessment.summary_json + '\n```', global_step=step)
        if artifact != 'none':
            directory = Path(report_dir) / slot / assessment.sha256
            directory.mkdir(parents=True, exist_ok=True)
            _files(directory, assessment, artifact)
        return LoggingResult('logged', assessment.sha256)
    except Exception as exc:
        if strict:
            raise
        return LoggingResult('error', assessment.sha256, type(exc).__name__)


def log_to_trackio(assessment: Assessment, *, run, step: int, slot='dataset',
                   artifact='none', strict=False):
    """Submit one history entry at an explicit caller-chosen Trackio step.

    Unlike W&B summary logging, Trackio advances its next-step counter even
    with an explicit step. Caller must plan training steps accordingly. No
    automatic deduplication. 'logged' means submitted, not confirmed durable:
    Trackio queues writes and may turn failures into warnings internally.
    """
    prefix = _validate(assessment, slot, artifact)
    if run is None:
        raise ValueError('An existing Trackio run is required')
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise ValueError('step must be a nonnegative integer')
    try:
        import trackio
        metrics, _ = _payload(assessment, prefix)
        metrics[f'{prefix}/assessment'] = trackio.Markdown(
            '```json\n' + assessment.summary_json + '\n```')
        run.log(metrics, step=step)
        if artifact != 'none':
            with tempfile.TemporaryDirectory(prefix='kalanos-tracking-') as directory:
                _files(directory, assessment, artifact)
                run.log_artifact(directory,
                                 name=f'kalanos-{slot}-{assessment.sha256[:16]}-{artifact}',
                                 type='dataset-assessment')
        return LoggingResult('logged', assessment.sha256)
    except Exception as exc:
        if strict:
            raise
        return LoggingResult('error', assessment.sha256, type(exc).__name__)
