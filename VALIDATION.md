# Validation record

What has been verified, and what has not. Update this file when you re-verify.

## Network-free unit tests

40 tests pass on CPython 3.10 and 3.12, with no tracker library installed. Coverage includes:
- Null readiness versus zero; separate descriptive score; missing coverage.
- Explicit numeric/metadata allowlist; private task/path/evidence exclusion.
- W&B summary-only behavior and artifact selection; MLflow run targeting.
- Same-report retry skipping and different-report slot conflicts for W&B/MLflow.
- SDK exceptions, strict mode, partial failures and privacy-safe error types.
- Trackio explicit step/history payload and artifacts.
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

## Not verified

- Hosted services (hosted W&B, a self-managed MLflow server, a Trackio Space).
- An actual training job, or any improvement in policy performance.
- The Microsoft Physical AI Toolchain insertion, which is documented but not executed.
- The `Real SDK smoke` workflow on a GitHub-hosted runner, until it has been run there.
- Windows and macOS runners.
