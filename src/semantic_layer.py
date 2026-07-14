import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb

AGG_MAP: dict[str, str] = {
    "sum": "SUM",
    "average": "AVG",
    "avg": "AVG",
    "max": "MAX",
    "min": "MIN",
    "count": "COUNT",
    "count_distinct": "COUNT",
    "median": "MEDIAN",
}

DEFAULT_MANIFEST_PATH = str(
    Path(__file__).resolve().parent.parent / "dbt_project" / "target" / "semantic_manifest.json"
)
DEFAULT_DUCKDB_PATH = str(
    Path(__file__).resolve().parent.parent / "dbt_project" / "target" / "dev.duckdb"
)


def _measure_sql(measure: dict) -> str:
    agg = measure.get("agg") or "sum"
    agg_func = AGG_MAP.get(agg, agg.upper())
    expr = measure.get("expr") or measure["name"]
    if agg == "count_distinct":
        return f"{agg_func}(DISTINCT {expr})"
    return f"{agg_func}({expr})"


class SemanticManifest:
    def __init__(self, manifest: dict) -> None:
        self._manifest = manifest
        self.metrics: dict[str, dict] = {
            m["name"]: m for m in manifest.get("metrics", [])
        }
        self.semantic_models: dict[str, dict] = {
            m["name"]: m for m in manifest.get("semantic_models", [])
        }
        self.measure_to_model: dict[str, dict] = {}
        self.measure_defs: dict[str, dict] = {}
        for model in manifest.get("semantic_models", []):
            for measure in model.get("measures", []):
                self.measure_to_model[measure["name"]] = model
                self.measure_defs[measure["name"]] = measure

    def get_all_metrics(self) -> list[dict]:
        return list(self.metrics.values())

    def get_all_semantic_models(self) -> list[dict]:
        return list(self.semantic_models.values())

    def get_metric(self, name: str) -> dict:
        metric = self.metrics.get(name)
        if metric is None:
            raise ValueError(f"Metric '{name}' not found in semantic manifest")
        return metric

    def get_semantic_model_for_metric(self, metric_name: str) -> dict:
        metric = self.get_metric(metric_name)
        if metric["type"] == "derived":
            input_metrics = metric["type_params"].get("metrics", [])
            if not input_metrics:
                raise ValueError(
                    f"Derived metric '{metric_name}' has no input metrics"
                )
            return self.get_semantic_model_for_metric(input_metrics[0]["name"])
        measure = metric["type_params"].get("measure")
        if measure is None:
            raise ValueError(f"Metric '{metric_name}' has no measure")
        model = self.measure_to_model.get(measure["name"])
        if model is None:
            raise ValueError(
                f"No semantic model found for measure '{measure['name']}'"
            )
        return model

    def get_dimensions_for_metric(self, metric_name: str) -> list[dict]:
        model = self.get_semantic_model_for_metric(metric_name)
        return model.get("dimensions", [])

    def get_entities_for_metric(self, metric_name: str) -> list[dict]:
        model = self.get_semantic_model_for_metric(metric_name)
        return model.get("entities", [])

    def _resolve_group_by(
        self, model: dict, group_by: list[str]
    ) -> list[tuple[str, str]]:
        lookup: dict[str, str] = {}
        for dim in model.get("dimensions", []):
            lookup[dim["name"]] = dim.get("expr") or dim["name"]
        for ent in model.get("entities", []):
            lookup[ent["name"]] = ent.get("expr") or ent["name"]
        resolved: list[tuple[str, str]] = []
        for name in group_by:
            col = lookup.get(name)
            if col is None:
                raise ValueError(
                    f"Dimension/entity '{name}' not found in semantic model '{model['name']}'"
                )
            resolved.append((name, col))
        return resolved


def load_manifest(manifest_path: str) -> SemanticManifest:
    with open(manifest_path) as f:
        data = json.load(f)
    return SemanticManifest(data)


def build_query_sql(
    manifest: SemanticManifest,
    metric_name: str,
    group_by: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int | None = None,
) -> str:
    metric = manifest.get_metric(metric_name)
    group_by = group_by or []

    if metric["type"] == "derived":
        expr_template = metric["type_params"].get("expr")
        if not expr_template:
            raise ValueError(f"Derived metric '{metric_name}' has no expr")
        input_metrics = metric["type_params"].get("metrics", [])
        if not input_metrics:
            raise ValueError(
                f"Derived metric '{metric_name}' has no input metrics"
            )

        agg_map: dict[str, str] = {}
        tables: set[str] = set()
        for inp in input_metrics:
            inp_name = inp["name"]
            inp_metric = manifest.get_metric(inp_name)
            if inp_metric["type"] != "simple":
                raise ValueError(
                    f"Input metric '{inp_name}' for derived metric "
                    f"'{metric_name}' must be a simple metric"
                )
            measure_ref = inp_metric["type_params"].get("measure")
            if measure_ref is None:
                raise ValueError(
                    f"Input metric '{inp_name}' has no measure"
                )
            model = manifest.measure_to_model.get(measure_ref["name"])
            if model is None:
                raise ValueError(
                    f"No semantic model for measure '{measure_ref['name']}'"
                )
            measure_def = manifest.measure_defs.get(measure_ref["name"])
            if measure_def is None:
                raise ValueError(
                    f"No measure definition for '{measure_ref['name']}'"
                )
            tables.add(model["node_relation"]["alias"])
            agg_map[inp_name] = _measure_sql(measure_def)

        if len(tables) > 1:
            raise ValueError(
                f"Input metrics for derived metric '{metric_name}' "
                f"span multiple tables: {sorted(tables)}"
            )
        table = tables.pop()

        names_sorted = sorted(agg_map, key=len, reverse=True)
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in names_sorted) + r")\b"
        )
        agg_expr = pattern.sub(lambda m: agg_map[m.group(1)], expr_template)

        model = manifest.get_semantic_model_for_metric(metric_name)
    else:
        measure_ref = metric["type_params"].get("measure")
        if measure_ref is None:
            raise ValueError(f"Metric '{metric_name}' has no measure")
        model = manifest.measure_to_model.get(measure_ref["name"])
        if model is None:
            raise ValueError(
                f"No semantic model for measure '{measure_ref['name']}'"
            )
        measure_def = manifest.measure_defs.get(measure_ref["name"])
        if measure_def is None:
            raise ValueError(
                f"No measure definition for '{measure_ref['name']}'"
            )
        table = model["node_relation"]["alias"]
        agg_expr = _measure_sql(measure_def)

    dim_exprs = manifest._resolve_group_by(model, group_by)

    select_parts: list[str] = []
    for name, col in dim_exprs:
        if col != name:
            select_parts.append(f"{col} AS {name}")
        else:
            select_parts.append(col)
    select_parts.append(f"{agg_expr} AS {metric_name}")
    select_clause = ", ".join(select_parts)

    sql = f"SELECT {select_clause}\nFROM {table}"

    where_parts: list[str] = []
    if start_date:
        where_parts.append(f"date_day >= '{start_date}'")
    if end_date:
        where_parts.append(f"date_day <= '{end_date}'")
    if where_parts:
        sql += "\nWHERE " + " AND ".join(where_parts)

    if dim_exprs:
        group_cols = ", ".join(col for _, col in dim_exprs)
        sql += f"\nGROUP BY {group_cols}"

    if limit is not None:
        sql += f"\nLIMIT {limit}"

    return sql


def main() -> None:
    manifest = load_manifest(DEFAULT_MANIFEST_PATH)

    print("=== Semantic Models ===")
    for model in manifest.get_all_semantic_models():
        nr = model["node_relation"]
        measures = ", ".join(m["name"] for m in model.get("measures", []))
        dims = ", ".join(d["name"] for d in model.get("dimensions", []))
        ents = ", ".join(e["name"] for e in model.get("entities", []))
        print(f"  {model['name']} -> {nr['alias']}")
        print(f"    measures: {measures}")
        print(f"    dimensions: {dims}")
        print(f"    entities: {ents}")

    print("\n=== Metrics ===")
    for metric in manifest.get_all_metrics():
        mtype = metric["type"]
        label = metric.get("label") or metric["name"]
        print(f"  {metric['name']} ({mtype}): {label}")

    print("\n=== Sample Queries ===")
    con = duckdb.connect(DEFAULT_DUCKDB_PATH, read_only=True)
    for metric in manifest.get_all_metrics():
        name = metric["name"]
        sql = build_query_sql(manifest, name)
        print(f"\n--- {name} ---")
        print(sql)
        try:
            result = con.execute(sql).fetchall()
            cols = [d[0] for d in con.description]
            print(f"  columns: {cols}")
            for row in result:
                print(f"  result: {row}")
        except Exception as exc:
            print(f"  [error] {exc}")
    con.close()


if __name__ == "__main__":
    main()
