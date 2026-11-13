"""Requires the mlflow and smoke extras. Run with: python examples/mlflow_local.py audit.json output-dir"""
import sys
from pathlib import Path
import mlflow
from mlflow.tracking import MlflowClient
from kalanos_tracking import load_assessment, log_to_mlflow

output = Path(sys.argv[2]).resolve()
output.mkdir(parents=True, exist_ok=True)
mlflow.set_tracking_uri(f'sqlite:///{output / "mlflow.db"}')
client = MlflowClient()
experiment = client.create_experiment('kalanos-local-smoke', artifact_location=(output/'artifacts').as_uri())
with mlflow.start_run(experiment_id=experiment) as run:
    result = log_to_mlflow(load_assessment(sys.argv[1]), run_id=run.info.run_id,
                          client=client, artifact='summary', strict=True)
    assert result.status == 'logged'
    saved = client.get_run(run.info.run_id)
    assert 'kalanos/dataset/episodes_total' in saved.data.metrics
    print(result)
