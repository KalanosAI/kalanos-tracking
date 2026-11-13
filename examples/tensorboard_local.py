"""Requires your existing torch+tensorboard, or tensorboardX installed separately."""
import sys
from pathlib import Path
from tensorboardX import SummaryWriter
from kalanos_tracking import load_assessment, log_to_tensorboard

output = Path(sys.argv[2]).resolve()
with SummaryWriter(str(output / 'events')) as writer:
    result = log_to_tensorboard(load_assessment(sys.argv[1]), writer=writer,
                               artifact='summary', report_dir=output / 'reports', strict=True)
    assert result.status == 'logged'
    print(result)
