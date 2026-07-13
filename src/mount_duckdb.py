import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

import duckdb

from src.config import (
    ALL_TOPICS,
    SCHEMAS,
    TOPIC_TO_DOMAIN,
    TOPIC_TO_TABLE,
    MinIOConfig,
)


def get_connection(db_path: str | None = None) -> duckdb.DuckDBPyConnection:
    if db_path is None:
        db_path = "data/compute.duckdb"
    if db_path != ":memory:":
        parent = Path(db_path).resolve().parent
        parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(db_path)
    con.execute("INSTALL httpfs;")
    con.execute("LOAD httpfs;")
    cfg = MinIOConfig.from_env()
    con.execute(f"SET s3_endpoint='{cfg.endpoint}';")
    con.execute("SET s3_use_ssl=false;")
    con.execute("SET s3_url_style='path';")
    con.execute(f"SET s3_access_key_id='{cfg.access_key}';")
    con.execute(f"SET s3_secret_access_key='{cfg.secret_key}';")
    return con


def mount_views(con: duckdb.DuckDBPyConnection) -> dict[str, str]:
    bucket = MinIOConfig.from_env().bucket
    views: dict[str, str] = {}
    for topic in ALL_TOPICS:
        domain = TOPIC_TO_DOMAIN[topic]
        table = TOPIC_TO_TABLE[topic]
        view_name = f"v_{table}"
        s3_uri = f"s3://{bucket}/{domain}/{table}/**/*.parquet"
        con.execute(
            f"CREATE OR REPLACE VIEW {view_name} AS "
            f"SELECT * FROM read_parquet('{s3_uri}', hive_partitioning = true)"
        )
        views[view_name] = s3_uri
    return views


def main() -> None:
    parser = argparse.ArgumentParser(description="Mount DuckDB views over MinIO Parquet files")
    parser.add_argument("--db-path", default=None, help="Path to DuckDB file (default: data/compute.duckdb)")
    parser.add_argument("--in-memory", action="store_true", help="Use an in-memory DuckDB database")
    args = parser.parse_args()

    db_path = ":memory:" if args.in_memory else args.db_path

    print("[mount_duckdb] Opening DuckDB connection...")
    con = get_connection(db_path)
    print(f"[mount_duckdb] DB path: {db_path or 'data/compute.duckdb'}")

    print("[mount_duckdb] Mounting views over MinIO Parquet files...")
    views = mount_views(con)

    print(f"[mount_duckdb] Created {len(views)} views:")
    for view_name, s3_uri in views.items():
        print(f"\n--- {view_name} ---")
        print(f"  Source: {s3_uri}")
        row_count = con.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
        print(f"  Row count: {row_count}")
        schema = con.execute(f"DESCRIBE {view_name}").fetchall()
        print("  Schema:")
        for col in schema:
            print(f"    {col[0]}  {col[1]}")

    print("\n[mount_duckdb] === Summary ===")
    for view_name in views:
        row_count = con.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
        print(f"  {view_name}: {row_count} rows")
    print("[mount_duckdb] Done.")


if __name__ == "__main__":
    main()
