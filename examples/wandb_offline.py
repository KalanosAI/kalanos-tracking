"""Run with: python examples/wandb_offline.py audit.json output-dir"""
import sys
from pathlib import Path
import wandb
from kalanos_tracking import load_assessment, log_to_wandb

output = Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
with wandb.init(project='kalanos-local-smoke', mode='offline', dir=str(output)) as run:
    result = log_to_wandb(load_assessment(sys.argv[1]), run=run,
                         artifact='summary', strict=True)
    assert result.status == 'logged'
    print(result)
