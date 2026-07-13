import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

import duckdb

from src.config import (
    ALL_TOPICS,
    SCHEMAS,
    TOPIC_TO_TABLE,
)
from src.mount_duckdb import get_connection, mount_views

TYPE_MAP: dict[str, str] = {
    "datetime": "TIMESTAMP",
    "str": "VARCHAR",
    "float64": "DOUBLE",
    "int32": "INTEGER",
    "int64": "BIGINT",
}

TABLE_TO_TOPIC: dict[str, str] = {v: k for k, v in TOPIC_TO_TABLE.items()}


def verify_row_counts(con: duckdb.DuckDBPyConnection, views: dict[str, str]) -> bool:
    print("\n[verify] === Row Counts ===")
    for view_name in views:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
            print(f"  {view_name}: {count} rows")
            if count == 0:
                print(f"  WARNING: {view_name} has 0 rows (data may not have been generated yet)")
        except Exception as e:
            print(f"  ERROR: Failed to query {view_name}: {e}")
            return False
    return True


def verify_schemas(con: duckdb.DuckDBPyConnection, views: dict[str, str]) -> bool:
    print("\n[verify] === Schema Validation ===")
    all_pass = True
    for view_name in views:
        table = view_name[2:]
        topic = TABLE_TO_TOPIC.get(table)
        if topic is None:
            print(f"  ERROR: No topic found for table '{table}'")
            all_pass = False
            continue

        expected: dict[str, str] = {}
        for col, type_str in SCHEMAS[topic].items():
            expected[col] = TYPE_MAP[type_str]
        expected["year"] = "BIGINT"
        expected["month"] = "VARCHAR"

        try:
            result = con.execute(f"DESCRIBE {view_name}").fetchall()
        except Exception as e:
            print(f"  ERROR: Failed to describe {view_name}: {e}")
            all_pass = False
            continue

        actual = {col[0]: col[1] for col in result}

        print(f"\n  {view_name}:")
        for col_name, expected_type in expected.items():
            if col_name not in actual:
                print(f"    FAIL: {col_name} ({expected_type}) — column missing")
                all_pass = False
            elif actual[col_name] != expected_type:
                print(f"    FAIL: {col_name} — expected {expected_type}, got {actual[col_name]}")
                all_pass = False
            else:
                print(f"    PASS: {col_name} ({expected_type})")
    return all_pass


def verify_nulls(con: duckdb.DuckDBPyConnection, views: dict[str, str]) -> bool:
    print("\n[verify] === Null Checks ===")
    all_pass = True
    for view_name in views:
        table = view_name[2:]
        topic = TABLE_TO_TOPIC.get(table)
        if topic is None:
            print(f"  ERROR: No topic found for table '{table}'")
            all_pass = False
            continue

        critical_cols = ["timestamp"]
        for col in SCHEMAS[topic]:
            if col.endswith("_id"):
                critical_cols.append(col)

        print(f"\n  {view_name}:")
        for col_name in critical_cols:
            try:
                null_count = con.execute(
                    f"SELECT COUNT(*) FROM {view_name} WHERE {col_name} IS NULL"
                ).fetchone()[0]
                if null_count > 0:
                    print(f"    FAIL: {col_name} has {null_count} null(s)")
                    all_pass = False
                else:
                    print(f"    PASS: {col_name} — no nulls")
            except Exception as e:
                print(f"    ERROR: Failed to check nulls in {view_name}.{col_name}: {e}")
                all_pass = False
    return all_pass


def verify_partitions(con: duckdb.DuckDBPyConnection, views: dict[str, str]) -> bool:
    print("\n[verify] === Partition Validation ===")
    all_pass = True
    for view_name in views:
        try:
            result = con.execute(
                f"SELECT DISTINCT tenant_id, year, month FROM {view_name} ORDER BY tenant_id, year, month"
            ).fetchall()
        except Exception as e:
            print(f"  ERROR: Failed to query partitions in {view_name}: {e}")
            all_pass = False
            continue

        print(f"\n  {view_name}:")
        if not result:
            print("    WARNING: No partition values found (view may be empty)")
            continue

        valid = True
        for row in result:
            tenant_id, year, month = row
            month_int = int(month)
            print(f"    tenant_id={tenant_id}, year={year}, month={month_int}")
            if not (1900 <= year <= 2100):
                print(f"      FAIL: invalid year {year}")
                valid = False
            if not (1 <= month_int <= 12):
                print(f"      FAIL: invalid month {month_int}")
                valid = False

        if valid:
            print("    PASS: all partition values valid")
        else:
            all_pass = False
    return all_pass


def verify_data(con: duckdb.DuckDBPyConnection) -> bool:
    print("[verify] Mounting views...")
    try:
        views = mount_views(con)
    except Exception as e:
        print(f"[verify] ERROR: Failed to mount views: {e}")
        return False

    print(f"[verify] Mounted {len(views)} views")

    results = {
        "row_counts": verify_row_counts(con, views),
        "schemas": verify_schemas(con, views),
        "nulls": verify_nulls(con, views),
        "partitions": verify_partitions(con, views),
    }

    print("\n[verify] === Summary ===")
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check}: {status}")

    all_pass = all(results.values())
    if all_pass:
        print("\n[verify] All checks passed.")
    else:
        print("\n[verify] Some checks failed.")
    return all_pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify data integrity in MinIO Parquet files")
    parser.add_argument("--db-path", default=None, help="Path to DuckDB file (default: data/compute.duckdb)")
    parser.add_argument("--in-memory", action="store_true", help="Use an in-memory DuckDB database")
    args = parser.parse_args()

    db_path = ":memory:" if args.in_memory else args.db_path

    print("[verify] Opening DuckDB connection...")
    con = get_connection(db_path)
    print(f"[verify] DB path: {db_path or 'data/compute.duckdb'}")

    passed = verify_data(con)

    if passed:
        print("[verify] Verification passed.")
        sys.exit(0)
    else:
        print("[verify] Verification failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
