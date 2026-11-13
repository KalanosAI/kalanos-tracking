"""Local-only smoke: python examples/trackio_local.py audit.json output-dir.

Reject remote destination environment settings before importing Trackio or creating
files. For intentional remote logging, use examples/trackio_existing_run.py.
"""
import os
import sys
from pathlib import Path

REMOTE_SETTINGS = ("TRACKIO_SPACE_ID", "TRACKIO_SERVER_URL", "TRACKIO_BUCKET_ID")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        raise SystemExit("Usage: python examples/trackio_local.py audit.json output-dir")
    configured = [key for key in REMOTE_SETTINGS if key in os.environ]
    if configured:
        # Never echo values: a destination URL may contain private information.
        raise SystemExit(
            "Local-only smoke refused: unset " + ", ".join(configured)
            + " and rerun. For intentional remote logging, use "
            "examples/trackio_existing_run.py with your configured run."
        )
    output = Path(argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ["TRACKIO_DIR"] = str(output)

    import trackio  # after environment validation and local storage configuration
    from kalanos_tracking import load_assessment, log_to_trackio

    run = trackio.init(project="kalanos-local-smoke", name="run")
    try:
        result = log_to_trackio(load_assessment(argv[0]), run=run, step=0,
                               slot="train_data", artifact="summary", strict=True)
        assert result.status == "logged", result
        trackio.log({"loss": 1.0}, step=1)
        print(result)
    finally:
        trackio.finish()


if __name__ == "__main__":
    main()
