"""Snippet to call after your application creates its Trackio run.

No init here: the caller chooses local/remote destination and owns the run.
"""
from kalanos_tracking import load_assessment, log_to_trackio


def attach_assessment(run, report_path, *, step):
    return log_to_trackio(load_assessment(report_path), run=run,
                         step=step, slot='train_data', artifact='summary')
