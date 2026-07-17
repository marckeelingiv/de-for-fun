import subprocess
import sys
from pathlib import Path
from typing import Mapping, Optional, Any

from dagster import AssetDep, AssetExecutionContext, AssetKey, Config, asset, ScheduleDefinition
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DBT_MANIFEST_PATH = PROJECT_ROOT / "dbt_project" / "target" / "manifest.json"

VERIFY_TIMEOUT = 120

VERIFIED_DATA_KEY = AssetKey(["minio_data_verified"])


class ProjectSandboxDbtTranslator(DagsterDbtTranslator):
    """Adds minio_data_verified as an upstream dependency for all dbt models."""

    def get_asset_spec(
        self,
        manifest: Mapping[str, Any],
        unique_id: str,
        project: Optional["DbtCliResource"],
    ):
        spec = super().get_asset_spec(manifest, unique_id, project)
        if unique_id.startswith("model."):
            spec = spec.merge_attributes(deps=[AssetDep(asset=VERIFIED_DATA_KEY)])
        return spec


@asset
def minio_data_verified(context: AssetExecutionContext) -> None:
    """Verify Parquet row counts, schema integrity, and partitions in MinIO."""
    context.log.info("Running data verification...")
    result = subprocess.run(
        [sys.executable, "src/verify_data.py"],
        capture_output=True,
        text=True,
        timeout=VERIFY_TIMEOUT,
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        context.log.error(result.stderr[-2000:])
        raise RuntimeError(f"Verification failed with code {result.returncode}")
    context.log.info(result.stdout[-2000:])


@dbt_assets(
    manifest=DBT_MANIFEST_PATH,
    dagster_dbt_translator=ProjectSandboxDbtTranslator(),
)
def project_sandbox_dbt(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
):
    """Run dbt build (models + tests) for the project_sandbox dbt project."""
    yield from dbt.cli(["build"], context=context).stream()


dbt_rebuild_schedule = ScheduleDefinition(
    name="dbt_rebuild_schedule",
    job_name="project_sandbox_dbt",
    cron_schedule="*/30 * * * *",
)
