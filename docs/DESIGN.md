# Design notes

## Layout

- `report.py`: snapshots local bytes, loads through official Kalanos validation, selects metrics/metadata and structured coverage.
- `trackers.py`: four caller-owned-run adapters, optional report artifacts, isolated slot state and explicit failure results.
- `tests/`: network-free tests of mapping, privacy, missing values, slot conflicts, artifacts and SDK failures.
- `examples/`: runnable offline/local smoke scripts using the real SDKs.

There is no custom JSON schema parser and no duplicated grading decisions. Kalanos is a pinned
report-loader dependency and is not modified by this package. `Assessment.sha256` identifies the
exact source bytes, not a dataset checksum or a report publisher signature. Compact and ordinary
serializations have distinct byte hashes.

## Write semantics

Partial tracker writes cannot be rolled back safely. For W&B and MLflow the completion marker
skips identical successful calls, not all retries or concurrent requests. One writer per run and
slot is required. The adapters are not designed for exactly-once distributed ingestion.
