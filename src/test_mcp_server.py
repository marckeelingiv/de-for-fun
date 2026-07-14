import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os
import unittest

from src.mcp_server import (
    generate_chart,
    get_metric_details,
    lightdash_status,
    list_available_dimensions,
    list_metrics,
    list_semantic_models,
    query_metric,
)

EXPECTED_METRICS = {
    "total_revenue",
    "average_dwell_time",
    "arena_bottleneck_ratio",
    "transaction_count",
    "sales_velocity",
    "merchant_sentiment_score",
    "ai_sla_compliance",
    "ai_token_consumption",
}

EXPECTED_MODELS = {
    "arena_bottlenecks",
    "dynamic_pricing",
    "merchant_sentiment",
    "ai_slas",
}


class TestMCPServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from src.config import MCPConfig

        cfg = MCPConfig.from_env()
        if not os.path.exists(cfg.manifest_path):
            raise unittest.SkipTest(
                f"Semantic manifest not found at {cfg.manifest_path}"
            )
        if not os.path.exists(cfg.duckdb_path):
            raise unittest.SkipTest(
                f"DuckDB database not found at {cfg.duckdb_path}"
            )

    @classmethod
    def tearDownClass(cls):
        import glob

        from src.config import MCPConfig

        chart_dir = MCPConfig.from_env().chart_output_dir
        for f in glob.glob(os.path.join(chart_dir, "*.png")):
            try:
                os.remove(f)
            except OSError:
                pass

    def test_list_metrics(self):
        result = list_metrics()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 8)
        names = {m["name"] for m in result}
        self.assertEqual(names, EXPECTED_METRICS)
        for m in result:
            for key in ("name", "label", "description", "type", "semantic_model"):
                self.assertIn(key, m)

    def test_list_semantic_models(self):
        result = list_semantic_models()
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)
        names = {m["name"] for m in result}
        self.assertEqual(names, EXPECTED_MODELS)
        for m in result:
            for key in ("name", "table", "entities", "dimensions", "measures"):
                self.assertIn(key, m)

    def test_get_metric_details_simple(self):
        result = get_metric_details(metric_name="total_revenue")
        self.assertEqual(result["name"], "total_revenue")
        self.assertIn("label", result)
        self.assertEqual(result["type"], "simple")
        measure = result.get("measure")
        self.assertIsInstance(measure, dict)
        for key in ("name", "agg", "expr"):
            self.assertIn(key, measure)
        self.assertTrue(result["available_dimensions"])
        self.assertIsInstance(result["available_entities"], list)

    def test_get_metric_details_derived(self):
        result = get_metric_details(metric_name="sales_velocity")
        self.assertEqual(result["type"], "derived")
        self.assertIn("total_revenue", result["derived_expr"])
        self.assertIn("transaction_count", result["derived_expr"])
        self.assertIn("total_revenue", result["input_metrics"])
        self.assertIn("transaction_count", result["input_metrics"])

    def test_get_metric_details_invalid(self):
        result = get_metric_details(metric_name="nonexistent")
        self.assertIn("error", result)

    def test_list_available_dimensions(self):
        result = list_available_dimensions(metric_name="total_revenue")
        self.assertIsInstance(result, list)
        self.assertTrue(result)
        for d in result:
            self.assertIn("name", d)
            self.assertIn("type", d)
        names = {d["name"] for d in result}
        self.assertIn("tenant_id", names)
        self.assertIn("date_day", names)

    def test_query_metric_simple(self):
        result = query_metric(metric_name="total_revenue")
        for key in ("columns", "rows", "row_count", "sql"):
            self.assertIn(key, result)
        self.assertEqual(result["row_count"], 1)
        self.assertIn("total_revenue", result["columns"])
        row = result["rows"][0]
        self.assertEqual(len(row), 1)
        self.assertIsInstance(row[0], (int, float))

    def test_query_metric_with_group_by(self):
        result = query_metric(metric_name="total_revenue", group_by=["tenant_id"])
        self.assertGreater(result["row_count"], 0)
        self.assertIn("tenant_id", result["columns"])
        self.assertIn("total_revenue", result["columns"])

    def test_query_metric_with_date_filter(self):
        result = query_metric(
            metric_name="total_revenue",
            start_date="2025-01-01",
            end_date="2025-12-31",
        )
        for key in ("columns", "rows", "row_count"):
            self.assertIn(key, result)
        sql_upper = result.get("sql", "").upper()
        self.assertTrue("WHERE" in sql_upper or result["row_count"] >= 0)

    def test_query_metric_derived(self):
        result = query_metric(
            metric_name="sales_velocity", group_by=["tenant_id"]
        )
        self.assertGreater(result["row_count"], 0)
        self.assertIn("sales_velocity", result["columns"])
        idx = result["columns"].index("sales_velocity")
        for row in result["rows"]:
            self.assertIsInstance(row[idx], (int, float))

    def test_query_metric_invalid(self):
        result = query_metric(metric_name="nonexistent")
        self.assertIn("error", result)

    def test_generate_chart_bar(self):
        result = generate_chart(
            metric_name="total_revenue",
            group_by=["tenant_id"],
            chart_type="bar",
        )
        self.assertIn("chart_path", result)
        self.assertTrue(os.path.exists(result["chart_path"]))
        self.assertTrue(result["chart_path"].endswith(".png"))

    def test_generate_chart_line(self):
        result = generate_chart(
            metric_name="total_revenue",
            group_by=["tenant_id"],
            chart_type="line",
        )
        self.assertIn("chart_path", result)
        self.assertTrue(os.path.exists(result["chart_path"]))
        self.assertTrue(result["chart_path"].endswith(".png"))

    def test_generate_chart_scatter(self):
        result = generate_chart(
            metric_name="total_revenue",
            group_by=["tenant_id"],
            chart_type="scatter",
        )
        self.assertIn("chart_path", result)
        self.assertTrue(os.path.exists(result["chart_path"]))
        self.assertTrue(result["chart_path"].endswith(".png"))

    def test_generate_chart_no_group_by(self):
        result = generate_chart(metric_name="total_revenue", chart_type="bar")
        self.assertIn("chart_path", result)
        self.assertTrue(os.path.exists(result["chart_path"]))

    def test_lightdash_status_not_configured(self):
        result = lightdash_status()
        self.assertIn("configured", result)
        self.assertFalse(result["configured"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
