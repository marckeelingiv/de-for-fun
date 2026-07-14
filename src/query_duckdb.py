import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

import duckdb

from src.mount_duckdb import mount_views, get_connection


def _print_results(title: str, rows: list, columns: list) -> None:
    print(f"\n=== {title} ===")
    print(" | ".join(str(col) for col in columns))
    print("-" * 40)
    for row in rows:
        print(" | ".join(str(val) for val in row))


def _run_query(con: duckdb.DuckDBPyConnection, title: str, sql: str) -> None:
    try:
        result = con.execute(sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()
    except Exception as exc:
        print(f"\n=== {title} ===")
        print(f"  [error] Query failed: {exc}")
        return
    _print_results(title, rows, columns)


def run_seg_queries(con: duckdb.DuckDBPyConnection) -> None:
    _run_query(
        con,
        "SEG: Fan Density by Beacon",
        """
        SELECT beacon_id, COUNT(*) AS ping_count, AVG(estimated_dwell_time) AS avg_dwell_time
        FROM v_fan_pings
        GROUP BY beacon_id
        ORDER BY ping_count DESC
        """,
    )
    _run_query(
        con,
        "SEG: Sales Velocity by Vendor and Item",
        """
        SELECT vendor_id, item_id, COUNT(*) AS transaction_count,
               SUM(amount) AS total_revenue, AVG(amount) AS avg_price
        FROM v_pos_transactions
        GROUP BY vendor_id, item_id
        ORDER BY total_revenue DESC
        """,
    )
    _run_query(
        con,
        "SEG: Hourly Revenue",
        """
        SELECT EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS tx_count, SUM(amount) AS revenue
        FROM v_pos_transactions
        GROUP BY hour
        ORDER BY hour
        """,
    )
    _run_query(
        con,
        "SEG: Payment Method Distribution",
        """
        SELECT payment_method, COUNT(*) AS tx_count, SUM(amount) AS total_amount
        FROM v_pos_transactions
        GROUP BY payment_method
        ORDER BY tx_count DESC
        """,
    )


def run_podium_queries(con: duckdb.DuckDBPyConnection) -> None:
    _run_query(
        con,
        "Podium: Top Merchants by Interaction Volume",
        """
        SELECT merchant_id, COUNT(*) AS interaction_count
        FROM v_interaction_events
        GROUP BY merchant_id
        ORDER BY interaction_count DESC
        LIMIT 10
        """,
    )
    _run_query(
        con,
        "Podium: Channel and Direction Breakdown",
        """
        SELECT channel, direction, COUNT(*) AS event_count
        FROM v_interaction_events
        GROUP BY channel, direction
        ORDER BY event_count DESC
        """,
    )
    _run_query(
        con,
        "Podium: AI Token Consumption Stats",
        """
        SELECT SUM(prompt_tokens) AS total_prompt, SUM(completion_tokens) AS total_completion,
               AVG(sentiment_score) AS avg_sentiment, AVG(latency_ms) AS avg_latency,
               COUNT(*) AS telemetry_count
        FROM v_ai_telemetry
        """,
    )
    _run_query(
        con,
        "Podium: Sentiment by Merchant",
        """
        SELECT e.merchant_id, COUNT(*) AS ai_interactions,
               AVG(t.sentiment_score) AS avg_sentiment, AVG(t.latency_ms) AS avg_latency,
               SUM(t.prompt_tokens + t.completion_tokens) AS total_tokens
        FROM v_interaction_events e
        JOIN v_ai_telemetry t ON e.interaction_id = t.interaction_id
        GROUP BY e.merchant_id
        ORDER BY ai_interactions DESC
        LIMIT 10
        """,
    )


def run_queries(con: duckdb.DuckDBPyConnection) -> None:
    run_seg_queries(con)
    run_podium_queries(con)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run analytical queries against DuckDB views over MinIO Parquet files"
    )
    parser.add_argument("--db-path", default=None, help="Path to DuckDB file (default: $DUCKDB_PATH or <repo>/dbt_project/target/dev.duckdb)")
    parser.add_argument("--in-memory", action="store_true", help="Use an in-memory DuckDB database")
    args = parser.parse_args()

    db_path = ":memory:" if args.in_memory else args.db_path
    if db_path is None:
        db_path = os.environ.get(
            "DUCKDB_PATH",
            str(Path(__file__).resolve().parent.parent / "dbt_project" / "target" / "dev.duckdb"),
        )

    print("[query_duckdb] Opening DuckDB connection...")
    con = get_connection(db_path)
    print(f"[query_duckdb] DB path: {db_path}")

    print("[query_duckdb] Mounting views over MinIO Parquet files...")
    views = mount_views(con)
    print(f"[query_duckdb] Mounted {len(views)} views: {', '.join(views.keys())}")

    print("[query_duckdb] Running analytical queries...")
    run_queries(con)

    print("\n[query_duckdb] === Summary ===")
    print(f"  Queries completed against {len(views)} views.")
    print("[query_duckdb] Done.")


if __name__ == "__main__":
    main()
