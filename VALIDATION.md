# Validation record

What has been verified, and what has not. Update this file when you re-verify.

## Network-free unit tests

At published base commit `58ae61d916dd10d6813ceeabc6e7f85267ca570b`, 40 tests passed on CPython 3.10 and 3.12 in GitHub CI. This follow-up patch passes **47 tests**, including seven local-example safeguard tests (author run: CPython 3.12 on macOS; re-run on Linux with CPython 3.10 and 3.12). The patched suite has not yet run in GitHub CI. Coverage includes:
- Null readiness versus zero; separate descriptive score; missing coverage.
- Explicit numeric/metadata allowlist; private task/path/evidence exclusion.
- W&B summary-only behavior and artifact selection; MLflow run targeting.
- Same-report retry skipping and different-report slot conflicts for W&B/MLflow.
- SDK exceptions, strict mode, partial failures and privacy-safe error types.
- Trackio explicit step/history payload and artifacts.
- Local Trackio example rejects remote destination variables (`TRACKIO_SPACE_ID`, `TRACKIO_SERVER_URL`, `TRACKIO_BUCKET_ID`) before initialization or file creation, including empty values, without exposing their values or altering the caller environment.
- TensorBoard scalars/text and explicitly located report sidecars.

These tests use SDK doubles. They are not hosted-service or actual SDK proof.

## Real SDK runs

A small synthetic CSV recording was graded with **Kalanos 0.9.3** (report schema 8.0.0), and each
shipped example was run against the real SDK on Linux with CPython 3.12, installing this package
with its extras:

| Library | Version | Result |
|---|---|---|
| W&B | 0.31.0 | `examples/wandb_offline.py` logged in offline mode. |
| MLflow-skinny | 3.18.0 | `examples/mlflow_local.py` logged to a SQLite store (SQLAlchemy 2.1.8 and Alembic) and read the metrics back. |
| TensorBoardX | 2.6.5 | `examples/tensorboard_local.py` logged scalars and text. |
| Trackio | 0.45.1 | `examples/trackio_local.py` logged locally. A SQLite read-back showed the assessment row at step 0 followed by the caller's own step 1. |

The exported metadata of that real report contained no local paths. Running the MLflow example
showed that the `smoke` extra needed Alembic; it is now included.

Earlier author-run checks on macOS (not re-run here) also covered ordinary schema-8 JSON, compact
encoding and metadata-tier reports with undefined readiness, `artifact="full"` byte-for-byte
round trips for W&B, MLflow and Trackio, and a TensorBoard event-reader check of scalars and text.

## Published GitHub verification

At exact commit `58ae61d916dd10d6813ceeabc6e7f85267ca570b`:
- [Unit CI](https://github.com/KalanosAI/kalanos-tracking/actions/runs/43360226546): 40 tests passed on Python 3.10 and 3.12.
- [Real SDK smoke](https://github.com/KalanosAI/kalanos-tracking/actions/runs/43360274837): successful on an Ubuntu GitHub-hosted runner with Python 3.12. It graded synthetic CSV data and ran all four shipped SDK examples.

**Hosted runner does not mean hosted tracker:** W&B was offline; MLflow, Trackio and TensorBoard used local storage. These results do not verify remote service delivery. Most smoke examples check SDK acceptance; only the MLflow example reads metrics back automatically.

For this follow-up patch, the revised Trackio local example also ran successfully with real Trackio 0.45.1 on macOS, and SQLite readback confirmed the assessment at step 0 followed by the caller's training entry at step 1. Remote-setting refusal and unchanged environment are covered by unit tests. No remote trackers were contacted for these checks.

Network behavior of that example was also observed on Linux with Trackio 0.45.1, with outbound connections blocked and recorded: with no destination variables set it attempted no external connection. An `HF_TOKEN` in the environment made Trackio attempt a Hugging Face username lookup, and `TRACKIO_BUCKET_ID` made it attempt a bucket sync (the example now refuses that variable). `TRACKIO_DATASET_ID` and `TRACKIO_WEBHOOK_URL` caused no connection attempt in this example.

## Not verified

- Hosted services (hosted W&B, a self-managed MLflow server, a Trackio Space).
- An actual training job, or any improvement in policy performance.
- The Microsoft Physical AI Toolchain insertion, which is documented but not executed.
- Windows and macOS GitHub-hosted runners; patched CI runs after applying this follow-up.
