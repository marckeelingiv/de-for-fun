import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class Domain(str, Enum):
    SEG = "arena"
    PODIUM = "podium"


class Topic(str, Enum):
    FAN_PINGS = "seg.fan-pings"
    POS_TRANSACTIONS = "seg.pos-transactions"
    INTERACTION_EVENTS = "podium.interaction-events"
    AI_TELEMETRY = "podium.ai-telemetry"


TOPIC_TO_DOMAIN: dict[str, str] = {
    Topic.FAN_PINGS.value: Domain.SEG.value,
    Topic.POS_TRANSACTIONS.value: Domain.SEG.value,
    Topic.INTERACTION_EVENTS.value: Domain.PODIUM.value,
    Topic.AI_TELEMETRY.value: Domain.PODIUM.value,
}

TOPIC_TO_TABLE: dict[str, str] = {
    Topic.FAN_PINGS.value: "fan_pings",
    Topic.POS_TRANSACTIONS.value: "pos_transactions",
    Topic.INTERACTION_EVENTS.value: "interaction_events",
    Topic.AI_TELEMETRY.value: "ai_telemetry",
}

ALL_TOPICS = [t.value for t in Topic]

SEG_TENANTS: list[str] = ["seg_001", "seg_002", "seg_003"]
PODIUM_TENANTS: list[str] = ["podium_001", "podium_002", "podium_003"]

FAN_PINGS_SCHEMA: dict[str, str] = {
    "tenant_id": "str",
    "timestamp": "datetime",
    "device_id": "str",
    "beacon_id": "str",
    "x_coord": "float64",
    "y_coord": "float64",
    "estimated_dwell_time": "int32",
}

POS_TRANSACTIONS_SCHEMA: dict[str, str] = {
    "tenant_id": "str",
    "timestamp": "datetime",
    "transaction_id": "str",
    "vendor_id": "str",
    "item_id": "str",
    "amount": "float64",
    "payment_method": "str",
}

INTERACTION_EVENTS_SCHEMA: dict[str, str] = {
    "tenant_id": "str",
    "timestamp": "datetime",
    "interaction_id": "str",
    "merchant_id": "str",
    "customer_id": "str",
    "channel": "str",
    "direction": "str",
}

AI_TELEMETRY_SCHEMA: dict[str, str] = {
    "tenant_id": "str",
    "timestamp": "datetime",
    "interaction_id": "str",
    "prompt_tokens": "int32",
    "completion_tokens": "int32",
    "sentiment_score": "float64",
    "latency_ms": "int32",
}

SCHEMAS: dict[str, dict[str, str]] = {
    Topic.FAN_PINGS.value: FAN_PINGS_SCHEMA,
    Topic.POS_TRANSACTIONS.value: POS_TRANSACTIONS_SCHEMA,
    Topic.INTERACTION_EVENTS.value: INTERACTION_EVENTS_SCHEMA,
    Topic.AI_TELEMETRY.value: AI_TELEMETRY_SCHEMA,
}


@dataclass(frozen=True)
class RedpandaConfig:
    brokers: str
    consumer_group: str

    @classmethod
    def from_env(cls) -> "RedpandaConfig":
        return cls(
            brokers=os.environ.get("REDPANDA_BROKERS", "localhost:9092"),
            consumer_group=os.environ.get("REDPANDA_CONSUMER_GROUP", "buffer-writer-group"),
        )


@dataclass(frozen=True)
class MinIOConfig:
    endpoint: str
    access_key: str
    secret_key: str
    secure: bool
    bucket: str

    @classmethod
    def from_env(cls) -> "MinIOConfig":
        raw_endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        endpoint = raw_endpoint.replace("http://", "").replace("https://", "")
        return cls(
            endpoint=endpoint,
            access_key=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
            secure=False,
            bucket=os.environ.get("MINIO_BUCKET", "data-lakehouse"),
        )


@dataclass(frozen=True)
class BufferConfig:
    batch_size: int
    idle_timeout_seconds: int

    @classmethod
    def from_env(cls) -> "BufferConfig":
        return cls(
            batch_size=int(os.environ.get("BUFFER_BATCH_SIZE", "10000")),
            idle_timeout_seconds=int(os.environ.get("BUFFER_IDLE_TIMEOUT", "30")),
        )


@dataclass(frozen=True)
class GeneratorConfig:
    default_rows: int
    full_scale_rows: int
    batch_size: int

    @classmethod
    def from_env(cls) -> "GeneratorConfig":
        return cls(
            default_rows=int(os.environ.get("GENERATOR_DEFAULT_ROWS", "100000")),
            full_scale_rows=int(os.environ.get("GENERATOR_FULL_SCALE_ROWS", "50000000")),
            batch_size=int(os.environ.get("GENERATOR_BATCH_SIZE", "5000")),
        )


@dataclass(frozen=True)
class LightdashConfig:
    url: str
    token: str
    project_uuid: str

    @classmethod
    def from_env(cls) -> "LightdashConfig":
        return cls(
            url=os.environ.get("LIGHTDASH_URL", ""),
            token=os.environ.get("LIGHTDASH_TOKEN", ""),
            project_uuid=os.environ.get("LIGHTDASH_PROJECT_UUID", ""),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.token)


@dataclass(frozen=True)
class MCPConfig:
    duckdb_path: str
    manifest_path: str
    chart_output_dir: str

    @classmethod
    def from_env(cls) -> "MCPConfig":
        project_root = Path(__file__).resolve().parent.parent
        return cls(
            duckdb_path=os.environ.get(
                "DUCKDB_PATH",
                str(project_root / "dbt_project" / "target" / "dev.duckdb"),
            ),
            manifest_path=os.environ.get(
                "SEMANTIC_MANIFEST_PATH",
                str(project_root / "dbt_project" / "target" / "semantic_manifest.json"),
            ),
            chart_output_dir=os.environ.get(
                "CHART_OUTPUT_DIR",
                str(project_root / "charts"),
            ),
        )


def build_partition_path(domain: str, table: str, tenant_id: str, year: int, month: int, batch_id: str) -> str:
    month_str = f"{month:02d}"
    return f"{domain}/{table}/tenant_id={tenant_id}/year={year}/month={month_str}/{batch_id}.parquet"


def build_s3_uri(domain: str, table: str, tenant_id: str, year: int, month: int, batch_id: str) -> str:
    path = build_partition_path(domain, table, tenant_id, year, month, batch_id)
    bucket = MinIOConfig.from_env().bucket
    return f"s3://{bucket}/{path}"


SCHEMA_TYPE_MAP: dict[str, Any] = {
    "datetime": "datetime",
    "str": "str",
    "float64": "float64",
    "int32": "int32",
    "int64": "int64",
}
