# Integration recipes

## W&B in an existing training process

Initialize your trainer's run normally, then call:

```python
from kalanos_tracking import load_assessment, log_to_wandb
result = log_to_wandb(load_assessment('audit.json'), run=run,
                     slot='train_data', artifact='summary')
if result.status == 'error':
    print(f'Assessment logging failed: {result.error_type}')
```

The adapter never calls `wandb.init`, `run.log`, `finish` or `login`. Run ownership stays with your training application. For separate train and validation reports use separate slots, e.g. `train_data` and `eval_data`. Do not attach a full-dataset audit as the assessed subset without regrading that subset.

## MLflow in an existing run

```python
from mlflow.tracking import MlflowClient
from kalanos_tracking import load_assessment, log_to_mlflow
client = MlflowClient()  # respects your existing tracking configuration
result = log_to_mlflow(load_assessment('audit.json'), run_id=run_id,
                      client=client, slot='train_data', artifact='summary')
```

Static assessment metrics are separate names at step 0. They do not change any active-run state. Logging to a finished run may be accepted by some MLflow backends but this is not promised; prefer the training startup hook.

## Microsoft Physical AI Toolchain

Official source reviewed:
- https://github.com/microsoft/physical-ai-toolchain/blob/main/training/il/scripts/lerobot/train.py
- https://github.com/microsoft/physical-ai-toolchain/blob/main/docs/evaluation/lerobot-evaluation.md

Proposed insertion: after its MLflow training run is initialized/resumed and before `lerobot-train` is launched. Read the run ID from that wrapper's actual run object, then call the helper above. Configure the report path in your own wrapper; **there is no existing Microsoft `--kalanos-report` flag**. Do not invent one in the command line.

For evaluation, attach the assessed evaluation dataset's report to the evaluation run. Dataset assessment and policy replay metrics (MSE/MAE/throughput) remain different kinds of evidence.

## Inspect without sending

```python
import json
from kalanos_tracking import load_assessment
assessment = load_assessment('audit.json')
print(json.dumps(assessment.summary, indent=2))
```

The summary contains only selected fields, but identifiers can still be private. The adapter does not infer whether a destination is approved for that data. Caller authorizes logging by invoking a tracker helper.

## Trackio

```python
from kalanos_tracking import load_assessment, log_to_trackio
result = log_to_trackio(load_assessment('audit.json'), run=trackio_run,
                       step=0, slot='train_data', artifact='summary')
```

The caller chooses step 0 (or another step) explicitly. This submits one history
entry with numeric metrics and Markdown metadata/coverage. It advances Trackio's
next-step counter. Call once, and plan subsequent training step values. The
adapter never initializes a Space or calls sync/finish. Existing run destination
and environment still control whether Trackio sends data remotely.

`logged` is submission, not a remote acknowledgement. Trackio can suppress
internal exceptions and buffer writes. Check local persistence after the caller
finishes/flushed its run; `strict=True` only propagates exceptions visible to the
helper, not failures hidden by the SDK.

## TensorBoard

Pass your existing `torch.utils.tensorboard.SummaryWriter` or compatible
`tensorboardX.SummaryWriter`. Scalars and JSON-formatted Text are written at the
chosen global step. No auto-close, no inferred training run, no step mutation.
For sidecars, select `artifact='summary'` or `'full'` and an explicit `report_dir`.
The report is a local file, not a TensorBoard-native artifact registry entry.
If your experiment platform syncs those directories, its permissions apply.

## API references

- W&B summary: https://docs.wandb.ai/models/track/log/log-summary
- MLflow tracking: https://mlflow.org/docs/latest/tracking/tracking-api/
- Trackio Run: https://github.com/gradio-app/trackio/blob/main/trackio/run.py
- TensorBoard SummaryWriter: https://docs.pytorch.org/docs/stable/tensorboard.html
