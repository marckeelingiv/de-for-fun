import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import asyncio
import io
import json
import signal
import time
import uuid
from dataclasses import replace

import polars as pl
import pyarrow.parquet as pq
from aiokafka import AIOKafkaConsumer
from aiokafka.structs import OffsetAndMetadata, TopicPartition
from minio import Minio
from minio.error import S3Error

from src.config import (
    ALL_TOPICS,
    SCHEMAS,
    TOPIC_TO_DOMAIN,
    TOPIC_TO_TABLE,
    BufferConfig,
    MinIOConfig,
    RedpandaConfig,
    build_partition_path,
)

POLARS_TYPE_MAP: dict[str, pl.DataType] = {
    "datetime": pl.Datetime,
    "str": pl.String,
    "float64": pl.Float64,
    "int32": pl.Int32,
    "int64": pl.Int64,
}


class TopicBuffer:
    def __init__(self, topic: str, minio_client: Minio, bucket: str, batch_size: int):
        self.topic = topic
        self.minio_client = minio_client
        self.bucket = bucket
        self.batch_size = batch_size
        self.domain = TOPIC_TO_DOMAIN[topic]
        self.table = TOPIC_TO_TABLE[topic]
        self.schema = SCHEMAS[topic]
        self.records: list[dict] = []
        self.last_flush_time: float = time.monotonic()
        self.committed_offsets: dict[int, int] = {}
        self.total_written: int = 0
        self.flush_count: int = 0

    def add(self, record: dict, partition: int, offset: int) -> None:
        self.records.append(record)
        current = self.committed_offsets.get(partition, -1)
        if offset > current:
            self.committed_offsets[partition] = offset
        self.last_flush_time = time.monotonic()

    def should_flush(self, idle_timeout: int, flush_interval: int | None = None) -> bool:
        if len(self.records) >= self.batch_size:
            return True
        if flush_interval is not None:
            if self.records and (time.monotonic() - self.last_flush_time) >= flush_interval:
                return True
            return False
        if self.records and (time.monotonic() - self.last_flush_time) >= idle_timeout:
            return True
        return False

    async def flush(self, consumer: AIOKafkaConsumer) -> int:
        if not self.records:
            return 0
        count = len(self.records)
        df = pl.DataFrame(self.records)
        for col_name, col_type in self.schema.items():
            if col_name not in df.columns:
                continue
            if col_type == "datetime":
                if df.schema[col_name] == pl.String:
                    df = df.with_columns(pl.col(col_name).str.to_datetime())
                else:
                    df = df.with_columns(pl.col(col_name).cast(pl.Datetime))
            else:
                df = df.with_columns(pl.col(col_name).cast(POLARS_TYPE_MAP[col_type]))
        df = df.with_columns(
            pl.col("timestamp").dt.year().alias("_year"),
            pl.col("timestamp").dt.month().alias("_month"),
        )
        partitions = df.partition_by(["_year", "_month", "tenant_id"], as_dict=True)
        for key, part_df in partitions.items():
            year, month, tenant_id = key[0], key[1], key[2]
            part_df = part_df.drop(["_year", "_month"])
            batch_id = f"batch_{uuid.uuid4().hex[:12]}"
            object_path = build_partition_path(
                self.domain, self.table, tenant_id, year, month, batch_id
            )
            table = part_df.to_arrow()
            out = io.BytesIO()
            pq.write_table(table, out)
            out.seek(0)
            size = out.getbuffer().nbytes
            await asyncio.to_thread(
                self.minio_client.put_object,
                self.bucket,
                object_path,
                out,
                size,
                "application/octet-stream",
            )
            print(
                f"[buffer_writer] Flushing topic {self.topic}: "
                f"{len(part_df)} records -> {object_path}"
            )
        offsets: dict[TopicPartition, OffsetAndMetadata] = {}
        for partition, offset in self.committed_offsets.items():
            tp = TopicPartition(self.topic, partition)
            offsets[tp] = OffsetAndMetadata(offset + 1, "")
        await consumer.commit(offsets)
        print(f"[buffer_writer] Committed offsets for {self.topic}")
        self.total_written += count
        self.flush_count += 1
        self.records.clear()
        self.committed_offsets.clear()
        self.last_flush_time = time.monotonic()
        return count


async def run(continuous: bool = False) -> None:
    redpanda = RedpandaConfig.from_env()
    minio_cfg = MinIOConfig.from_env()
    buffer_cfg = BufferConfig.from_env()
    if continuous:
        buffer_cfg = replace(buffer_cfg, continuous=True)

    print(f"[buffer_writer] Redpanda brokers: {redpanda.brokers}")
    print(f"[buffer_writer] MinIO endpoint: {minio_cfg.endpoint}, bucket: {minio_cfg.bucket}")
    print(
        f"[buffer_writer] Batch size: {buffer_cfg.batch_size}, "
        f"idle timeout: {buffer_cfg.idle_timeout_seconds}s"
    )
    if buffer_cfg.continuous:
        print(f"[buffer_writer] Continuous mode: flush every {buffer_cfg.flush_interval_seconds}s")
    else:
        print(f"[buffer_writer] Idle timeout: {buffer_cfg.idle_timeout_seconds}s")

    minio_client = Minio(
        minio_cfg.endpoint,
        access_key=minio_cfg.access_key,
        secret_key=minio_cfg.secret_key,
        secure=minio_cfg.secure,
    )

    consumer = AIOKafkaConsumer(
        *ALL_TOPICS,
        bootstrap_servers=redpanda.brokers,
        group_id=redpanda.consumer_group,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )

    buffers: dict[str, TopicBuffer] = {
        topic: TopicBuffer(topic, minio_client, minio_cfg.bucket, buffer_cfg.batch_size)
        for topic in ALL_TOPICS
    }

    shutdown_event = asyncio.Event()

    def _request_shutdown() -> None:
        print("\n[buffer_writer] Shutdown signal received.")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _request_shutdown)

    print(f"[buffer_writer] Starting consumer (group: {redpanda.consumer_group})...")
    await consumer.start()
    print(f"[buffer_writer] Subscribed to {len(ALL_TOPICS)} topics: {', '.join(ALL_TOPICS)}")

    flush_interval = buffer_cfg.flush_interval_seconds if buffer_cfg.continuous else None
    idle_timeout = buffer_cfg.idle_timeout_seconds

    try:
        while not shutdown_event.is_set():
            try:
                batches = await consumer.getmany(timeout_ms=1000)
            except Exception as exc:
                print(f"[buffer_writer] Error polling messages: {exc}")
                await asyncio.sleep(1)
                continue

            for tp, messages in batches.items():
                topic_buf = buffers[tp.topic]
                for msg in messages:
                    topic_buf.add(msg.value, msg.partition, msg.offset)

            for topic, topic_buf in buffers.items():
                if topic_buf.should_flush(idle_timeout, flush_interval):
                    if flush_interval is not None and len(topic_buf.records) < topic_buf.batch_size:
                        print(
                            f"[buffer_writer] Flush interval reached for {topic}, "
                            f"flushing {len(topic_buf.records)} records..."
                        )
                    elif flush_interval is None and len(topic_buf.records) < topic_buf.batch_size:
                        print(
                            f"[buffer_writer] Idle timeout reached for {topic}, "
                            f"flushing {len(topic_buf.records)} records..."
                        )
                    try:
                        await topic_buf.flush(consumer)
                    except S3Error as exc:
                        print(f"[buffer_writer] MinIO error flushing {topic}: {exc}")
                    except Exception as exc:
                        print(f"[buffer_writer] Error flushing {topic}: {exc}")

        print("[buffer_writer] Shutting down, flushing remaining buffers...")
        for topic, topic_buf in buffers.items():
            if topic_buf.records:
                print(
                    f"[buffer_writer] Flushing remaining "
                    f"{len(topic_buf.records)} records for {topic}..."
                )
                try:
                    await topic_buf.flush(consumer)
                except Exception as exc:
                    print(f"[buffer_writer] Error flushing {topic} during shutdown: {exc}")

        print("[buffer_writer] === Final Summary ===")
        for topic, topic_buf in buffers.items():
            print(
                f"  {topic}: {topic_buf.total_written} records written "
                f"in {topic_buf.flush_count} flushes"
            )
    finally:
        await consumer.stop()
        print("[buffer_writer] Consumer stopped. Bye!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Buffer writer (Redpanda -> MinIO Parquet)")
    parser.add_argument(
        "--continuous",
        action="store_true",
        default=False,
        help="Run in continuous mode (never exit on idle, flush on interval).",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(continuous=args.continuous))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
