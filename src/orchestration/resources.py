from dagster_dbt import DbtCliResource

DBT_PROJECT_DIR = "dbt_project"
DBT_PROFILES_DIR = "dbt_project"

dbt_resource = DbtCliResource(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=DBT_PROFILES_DIR,
)
