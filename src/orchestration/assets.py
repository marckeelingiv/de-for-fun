import subprocess
import sys
from pathlib import Path
from typing import Mapping, Optional, Any

from dagster import AssetDep, AssetExecutionContext, AssetIn, AssetKey, Config, asset
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DBT_MANIFEST_PATH = PROJECT_ROOT / "dbt_project" / "target" / "manifest.json"

GENERATOR_TIMEOUT = 600
BUFFER_WRITER_TIMEOUT = 120
VERIFY_TIMEOUT = 120

VERIFIED_DATA_KEY = AssetKey(["minio_data_verified"])


class GeneratorAssetConfig(Config):
    rows: int = 100000


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
def synthetic_data(context: AssetExecutionContext, config: GeneratorAssetConfig) -> None:
    """Generate synthetic SEG and Podium data and stream to Redpanda."""
    context.log.info(f"Generating {config.rows} synthetic rows...")
    result = subprocess.run(
        [sys.executable, "src/generator.py", "--rows", str(config.rows)],
        capture_output=True,
        text=True,
        timeout=GENERATOR_TIMEOUT,
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        context.log.error(result.stderr[-2000:])
        raise RuntimeError(f"Generator failed with code {result.returncode}")
    context.log.info(result.stdout[-2000:])


@asset(ins={"synthetic_data": AssetIn()})
def buffered_parquet(context: AssetExecutionContext, synthetic_data) -> None:
    """Consume from Redpanda and write partitioned Parquet to MinIO."""
    context.log.info("Starting buffer writer (Redpanda -> MinIO Parquet)...")
    try:
        result = subprocess.run(
            [sys.executable, "src/buffer_writer.py"],
            capture_output=True,
            text=True,
            timeout=BUFFER_WRITER_TIMEOUT,
            cwd=PROJECT_ROOT,
        )
        if result.returncode != 0:
            context.log.error(result.stderr[-2000:])
            raise RuntimeError(f"Buffer writer failed with code {result.returncode}")
        context.log.info(result.stdout[-2000:])
    except subprocess.TimeoutExpired:
        context.log.info("Buffer writer timed out (expected for long-running consumer).")


@asset(ins={"buffered_parquet": AssetIn()})
def minio_data_verified(context: AssetExecutionContext, buffered_parquet) -> None:
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
