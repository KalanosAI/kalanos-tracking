"""Requires the trackio extra. Run with: python examples/trackio_local.py audit.json output-dir

Creates a local-only Trackio run in output-dir, attaches the assessment at step 0,
then writes one training step. It launches no training and uses no remote destination.
"""
import os
import sys
from pathlib import Path

output = Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
os.environ["TRACKIO_DIR"] = str(output)  # keep this smoke run local

import trackio  # noqa: E402  (after TRACKIO_DIR is set)
from kalanos_tracking import load_assessment, log_to_trackio  # noqa: E402

run = trackio.init(project="kalanos-local-smoke", name="run")
result = log_to_trackio(load_assessment(sys.argv[1]), run=run, step=0,
                        slot="train_data", artifact="summary", strict=True)
assert result.status == "logged", result
trackio.log({"loss": 1.0}, step=1)  # the caller's training continues at the next step
trackio.finish()
print(result)
