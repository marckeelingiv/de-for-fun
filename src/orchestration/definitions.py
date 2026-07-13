from dagster import Definitions

from src.orchestration.assets import (
    buffered_parquet,
    minio_data_verified,
    project_sandbox_dbt,
    synthetic_data,
)
from src.orchestration.resources import DBT_PROFILES_DIR, DBT_PROJECT_DIR, dbt_resource

defs = Definitions(
    assets=[
        synthetic_data,
        buffered_parquet,
        minio_data_verified,
        project_sandbox_dbt,
    ],
    resources={
        "dbt": dbt_resource,
    },
)
