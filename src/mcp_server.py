import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import json
import os
import urllib.request
from datetime import datetime
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from fastmcp import FastMCP

from src.config import LightdashConfig, MCPConfig
from src.semantic_layer import SemanticManifest, build_query_sql, load_manifest

try:
    _mcp_cfg = MCPConfig.from_env()
    manifest: SemanticManifest | None = load_manifest(_mcp_cfg.manifest_path)
except Exception as exc:
    manifest = None
    _manifest_load_error = str(exc)
_mcp_cfg = MCPConfig.from_env()

mcp = FastMCP(
    name="project-sandbox-mcp",
    instructions=(
        "Project Sandbox MCP server for querying dbt semantic layer metrics.\n"
        "Available metrics: total_revenue, average_dwell_time, "
        "arena_bottleneck_ratio, transaction_count, sales_velocity, "
        "merchant_sentiment_score, ai_sla_compliance, ai_token_consumption.\n"
        "Available semantic models: arena_bottlenecks, dynamic_pricing, "
        "merchant_sentiment, ai_slas.\n"
        "Use list_metrics to discover metrics, get_metric_details for schema info, "
        "query_metric to run bounded queries, and generate_chart for visualizations.\n"
        "Lightdash integration tools are available when LIGHTDASH_URL is configured."
    ),
)

_NOT_LOADED = {
    "error": (
        "Semantic manifest not loaded. Ensure the dbt project has been compiled "
        "and the semantic_manifest.json file exists."
    )
}

_DARK_FIGCOLOR = "#1a1a2e"
_DARK_AXCOLOR = "#16213e"
_DARK_TEXTCOLOR = "#e0e0e0"
_DARK_GRIDCOLOR = "#333333"
_DARK_COLOR_CYCLE = [
    "#00d4ff",
    "#ff6b6b",
    "#feca57",
    "#48dbfb",
    "#1dd1a1",
    "#ff9ff3",
    "#a55eea",
    "#fd79a8",
]


def _require_manifest() -> SemanticManifest | dict:
    if manifest is None:
        return _NOT_LOADED
    return manifest


@mcp.tool()
def list_metrics() -> list[dict]:
    """List all available metrics from the dbt semantic layer."""
    m = _require_manifest()
    if isinstance(m, dict):
        return [m]
    result: list[dict] = []
    for metric in m.get_all_metrics():
        model = m.get_semantic_model_for_metric(metric["name"])
        result.append(
            {
                "name": metric["name"],
                "label": metric.get("label") or metric["name"],
                "description": metric.get("description") or "",
                "type": metric["type"],
                "semantic_model": model["name"],
            }
        )
    return result


@mcp.tool()
def list_semantic_models() -> list[dict]:
    """List all semantic models with their entities, dimensions, and measures."""
    m = _require_manifest()
    if isinstance(m, dict):
        return [m]
    result: list[dict] = []
    for model in m.get_all_semantic_models():
        nr = model.get("node_relation") or {}
        result.append(
            {
                "name": model["name"],
                "description": model.get("description") or "",
                "table": nr.get("alias", ""),
                "entities": [
                    {"name": e["name"], "type": e["type"]}
                    for e in model.get("entities", [])
                ],
                "dimensions": [
                    {
                        "name": d["name"],
                        "type": d["type"],
                        "expr": d.get("expr"),
                    }
                    for d in model.get("dimensions", [])
                ],
                "measures": [
                    {
                        "name": ms["name"],
                        "agg": ms.get("agg"),
                        "expr": ms.get("expr"),
                    }
                    for ms in model.get("measures", [])
                ],
            }
        )
    return result


@mcp.tool()
def get_metric_details(metric_name: str) -> dict:
    """Get detailed information about a specific metric including its measure and available dimensions."""
    m = _require_manifest()
    if isinstance(m, dict):
        return m
    try:
        metric = m.get_metric(metric_name)
    except ValueError as exc:
        return {"error": str(exc)}
    model = m.get_semantic_model_for_metric(metric_name)
    details: dict = {
        "name": metric["name"],
        "label": metric.get("label") or metric["name"],
        "description": metric.get("description") or "",
        "type": metric["type"],
        "semantic_model": model["name"],
        "available_dimensions": [d["name"] for d in m.get_dimensions_for_metric(metric_name)],
        "available_entities": [e["name"] for e in m.get_entities_for_metric(metric_name)],
    }
    if metric["type"] == "simple":
        measure_ref = metric["type_params"].get("measure")
        measure_def = m.measure_defs.get(measure_ref["name"]) if measure_ref else None
        if measure_def:
            details["measure"] = {
                "name": measure_def["name"],
                "agg": measure_def.get("agg"),
                "expr": measure_def.get("expr"),
            }
        else:
            details["measure"] = None
    else:
        details["measure"] = None
        details["derived_expr"] = metric["type_params"].get("expr")
        details["input_metrics"] = [
            inp["name"] for inp in metric["type_params"].get("metrics", [])
        ]
    return details


@mcp.tool()
def list_available_dimensions(metric_name: str) -> list[dict]:
    """List dimensions and entities that can be used for group_by with a given metric."""
    m = _require_manifest()
    if isinstance(m, dict):
        return [m]
    try:
        metric = m.get_metric(metric_name)
    except ValueError as exc:
        return [{"error": str(exc)}]
    dims = m.get_dimensions_for_metric(metric_name)
    ents = m.get_entities_for_metric(metric_name)
    result: list[dict] = []
    for d in dims:
        result.append({"name": d["name"], "type": d["type"], "expr": d.get("expr")})
    for e in ents:
        result.append({"name": e["name"], "type": e["type"], "expr": e.get("expr")})
    return result


@mcp.tool()
def query_metric(
    metric_name: str,
    group_by: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
) -> dict:
    """Execute a metric query against DuckDB and return rows, columns, and the generated SQL."""
    m = _require_manifest()
    if isinstance(m, dict):
        return m
    try:
        sql = build_query_sql(
            m, metric_name, group_by, start_date, end_date, limit
        )
    except Exception as exc:
        return {"error": f"Failed to build query: {exc}"}
    try:
        con = duckdb.connect(_mcp_cfg.duckdb_path, read_only=True)
        result = con.execute(sql)
        columns = [d[0] for d in result.description]
        rows = [list(r) for r in result.fetchall()]
        con.close()
    except Exception as exc:
        return {"error": f"DuckDB query failed: {exc}"}
    return {
        "metric": metric_name,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


@mcp.tool()
def generate_chart(
    metric_name: str,
    group_by: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = 100,
    chart_type: str = "bar",
) -> dict:
    """Run a metric query and generate a dark-themed chart PNG saved to the chart output directory."""
    m = _require_manifest()
    if isinstance(m, dict):
        return m
    query_result = query_metric(
        metric_name, group_by, start_date, end_date, limit
    )
    if "error" in query_result:
        return query_result
    columns = query_result["columns"]
    rows = query_result["rows"]
    metric_label = metric_name
    try:
        metric = m.get_metric(metric_name)
        metric_label = metric.get("label") or metric_name
    except ValueError:
        pass

    output_dir = Path(_mcp_cfg.chart_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{metric_name}_{chart_type}_{timestamp}.png"
    chart_path = output_dir / filename

    values = [r[-1] for r in rows]
    if group_by:
        x_labels = [str(r[0]) for r in rows]
        xlabel = group_by[0]
    else:
        x_labels = [metric_label]
        xlabel = "Total"
    x_positions = list(range(len(x_labels)))

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    fig.patch.set_facecolor(_DARK_FIGCOLOR)
    ax.set_facecolor(_DARK_AXCOLOR)
    ax.tick_params(colors=_DARK_TEXTCOLOR)
    for spine in ax.spines.values():
        spine.set_color(_DARK_GRIDCOLOR)
    ax.xaxis.label.set_color(_DARK_TEXTCOLOR)
    ax.yaxis.label.set_color(_DARK_TEXTCOLOR)
    ax.title.set_color(_DARK_TEXTCOLOR)
    ax.grid(True, color=_DARK_GRIDCOLOR, alpha=0.3)

    bar_color = _DARK_COLOR_CYCLE[0]
    if chart_type == "bar":
        ax.bar(x_positions, values, color=bar_color)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    elif chart_type == "line":
        ax.plot(x_positions, values, color=bar_color, marker="o")
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    elif chart_type == "scatter":
        ax.scatter(x_positions, values, color=bar_color, s=80)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    else:
        plt.close(fig)
        return {"error": f"Unsupported chart_type '{chart_type}'. Use bar, line, or scatter."}

    ax.set_title(metric_label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(metric_label)
    fig.tight_layout()
    fig.savefig(str(chart_path), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

    return {
        "metric": metric_name,
        "chart_path": str(chart_path),
        "chart_type": chart_type,
        "row_count": len(rows),
    }


def _lightdash_get(url: str, token: str, path: str) -> dict:
    full_url = f"{url}{path}"
    req = urllib.request.Request(
        full_url,
        headers={
            "Authorization": f"ApiKey {token}",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


_NOT_CONFIGURED = {
    "configured": False,
    "message": "Lightdash not configured. Set LIGHTDASH_URL and LIGHTDASH_TOKEN env vars.",
}


@mcp.tool()
def lightdash_status() -> dict:
    """Check if Lightdash is configured and reachable, listing projects if available."""
    cfg = LightdashConfig.from_env()
    if not cfg.is_configured:
        return _NOT_CONFIGURED
    try:
        data = _lightdash_get(cfg.url, cfg.token, "/api/v1/org/projects")
        projects = data.get("results", data) if isinstance(data, dict) else data
        return {
            "configured": True,
            "reachable": True,
            "projects": projects,
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "error": str(exc),
        }


@mcp.tool()
def lightdash_list_charts() -> dict:
    """List charts from the configured Lightdash project."""
    cfg = LightdashConfig.from_env()
    if not cfg.is_configured:
        return _NOT_CONFIGURED
    try:
        data = _lightdash_get(
            cfg.url, cfg.token, f"/api/v1/projects/{cfg.project_uuid}/charts"
        )
        return data
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def lightdash_get_catalog() -> dict:
    """Get the data catalog from the configured Lightdash project."""
    cfg = LightdashConfig.from_env()
    if not cfg.is_configured:
        return _NOT_CONFIGURED
    try:
        data = _lightdash_get(
            cfg.url, cfg.token, f"/api/v1/projects/{cfg.project_uuid}/dataCatalog"
        )
        return data
    except Exception as exc:
        return {"error": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Project Sandbox MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8079)
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="http", host="0.0.0.0", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
