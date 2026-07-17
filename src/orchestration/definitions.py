from dagster import Definitions

from src.orchestration.assets import (
    dbt_rebuild_schedule,
    minio_data_verified,
    project_sandbox_dbt,
)
from src.orchestration.resources import dbt_resource

defs = Definitions(
    assets=[
        minio_data_verified,
        project_sandbox_dbt,
    ],
    resources={
        "dbt": dbt_resource,
    },
    schedules=[dbt_rebuild_schedule],
)
