import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import asyncio
import json
import random
import uuid
from datetime import datetime, timedelta

import polars as pl
from aiokafka import AIOKafkaProducer

from src.config import GeneratorConfig, RedpandaConfig, Topic, PODIUM_TENANTS

MERCHANT_POOL_SIZE = 200
CUSTOMER_POOL_SIZE = 10_000
AI_COVERAGE = 0.70

_BUSINESS_HOURS = list(range(9, 18))
_HOUR_WEIGHTS = [1.0, 3.0, 1.5, 1.0, 1.0, 2.5, 2.5, 1.5, 1.0]
_CHANNELS = ["SMS", "Web"]
_CHANNEL_WEIGHTS = [60.0, 40.0]
_DIRECTIONS = ["Inbound", "Outbound"]
_DIRECTION_WEIGHTS = [40.0, 60.0]


def _random_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128)))


def _generate_pools(seed: int) -> tuple[list[str], list[float], list[str]]:
    rng = random.Random(seed)
    merchants = [_random_uuid(rng) for _ in range(MERCHANT_POOL_SIZE)]
    top_count = MERCHANT_POOL_SIZE // 5
    merchant_weights = [16.0] * top_count + [1.0] * (MERCHANT_POOL_SIZE - top_count)
    rng.shuffle(merchant_weights)
    customers = [_random_uuid(rng) for _ in range(CUSTOMER_POOL_SIZE)]
    return merchants, merchant_weights, customers


def _generate_business_timestamps(n: int, rng: random.Random) -> list[datetime]:
    base = datetime(2024, 1, 1)
    timestamps: list[datetime] = []
    for _ in range(n):
        d = base + timedelta(days=rng.randint(0, 364))
        while d.weekday() >= 5:
            d += timedelta(days=1)
        hour = rng.choices(_BUSINESS_HOURS, weights=_HOUR_WEIGHTS)[0]
        minute = rng.randint(0, 59)
        second = rng.randint(0, 59)
        timestamps.append(datetime(d.year, d.month, d.day, hour, minute, second))
    return timestamps


def generate_interaction_events(
    num_rows: int,
    seed: int,
    pools: tuple[list[str], list[float], list[str]] | None = None,
) -> pl.DataFrame:
    if pools is None:
        pools = _generate_pools(seed)
    merchants, merchant_weights, customers = pools
    rng = random.Random(seed)
    interaction_ids = [_random_uuid(rng) for _ in range(num_rows)]
    timestamps = _generate_business_timestamps(num_rows, rng)
    merchant_ids = rng.choices(merchants, weights=merchant_weights, k=num_rows)
    customer_ids = rng.choices(customers, k=num_rows)
    channels = rng.choices(_CHANNELS, weights=_CHANNEL_WEIGHTS, k=num_rows)
    directions = rng.choices(_DIRECTIONS, weights=_DIRECTION_WEIGHTS, k=num_rows)
    tenant_ids = rng.choices(PODIUM_TENANTS, k=num_rows)
    return pl.DataFrame(
        {
            "tenant_id": tenant_ids,
            "interaction_id": interaction_ids,
            "timestamp": timestamps,
            "merchant_id": merchant_ids,
            "customer_id": customer_ids,
            "channel": channels,
            "direction": directions,
        },
        schema={
            "tenant_id": pl.Utf8,
            "interaction_id": pl.Utf8,
            "timestamp": pl.Datetime,
            "merchant_id": pl.Utf8,
            "customer_id": pl.Utf8,
            "channel": pl.Utf8,
            "direction": pl.Utf8,
        },
    )


def generate_ai_telemetry(interaction_ids: list[str], seed: int) -> pl.DataFrame:
    rng = random.Random(seed)
    n = len(interaction_ids)
    timestamps = _generate_business_timestamps(n, rng)
    tenant_ids = rng.choices(PODIUM_TENANTS, k=n)
    prompt_tokens: list[int] = []
    completion_tokens: list[int] = []
    sentiment_scores: list[float] = []
    latencies: list[int] = []
    for _ in range(n):
        pt = max(50, min(800, int(50 + rng.betavariate(2, 5) * 750)))
        prompt_tokens.append(pt)
        ratio = max(0.2, min(0.8, rng.gauss(0.5, 0.12)))
        completion_tokens.append(max(20, min(500, int(pt * ratio))))
        sentiment_scores.append(max(-1.0, min(1.0, rng.gauss(0.1, 0.35))))
        latencies.append(max(50, min(5000, int(rng.lognormvariate(5.5, 0.6)))))
    return pl.DataFrame(
        {
            "tenant_id": tenant_ids,
            "timestamp": timestamps,
            "interaction_id": interaction_ids,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "sentiment_score": sentiment_scores,
            "latency_ms": latencies,
        },
        schema={
            "tenant_id": pl.Utf8,
            "timestamp": pl.Datetime,
            "interaction_id": pl.Utf8,
            "prompt_tokens": pl.Int32,
            "completion_tokens": pl.Int32,
            "sentiment_score": pl.Float64,
            "latency_ms": pl.Int32,
        },
    )


def _json_default(obj: object) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def produce_to_kafka(
    producer: AIOKafkaProducer, topic: str, df: pl.DataFrame
) -> int:
    records = df.to_dicts()
    count = 0
    for record in records:
        payload = json.dumps(record, default=_json_default).encode("utf-8")
        await producer.send_and_wait(topic, value=payload)
        count += 1
    return count


async def run(rows: int, batch_size: int, seed: int) -> None:
    redpanda = RedpandaConfig.from_env()
    producer = AIOKafkaProducer(bootstrap_servers=redpanda.brokers)
    print(f"[generator_podium] Connecting to Redpanda at {redpanda.brokers}...")
    await producer.start()
    try:
        pools = _generate_pools(seed)
        interaction_total = 0
        all_interaction_ids: list[str] = []
        batch_index = 0
        for offset in range(0, rows, batch_size):
            n = min(batch_size, rows - offset)
            df = generate_interaction_events(n, seed + batch_index, pools=pools)
            sent = await produce_to_kafka(
                producer, Topic.INTERACTION_EVENTS.value, df
            )
            interaction_total += sent
            all_interaction_ids.extend(df["interaction_id"].to_list())
            batch_index += 1
            print(
                f"[generator_podium] Produced "
                f"{interaction_total}/{rows} interaction_events..."
            )

        ai_rng = random.Random(seed)
        ai_count = int(len(all_interaction_ids) * AI_COVERAGE)
        ai_ids = ai_rng.sample(all_interaction_ids, ai_count)
        telemetry_total = 0
        batch_index = 0
        for offset in range(0, ai_count, batch_size):
            n = min(batch_size, ai_count - offset)
            batch_ids = ai_ids[offset : offset + n]
            df = generate_ai_telemetry(batch_ids, seed + 10_000 + batch_index)
            sent = await produce_to_kafka(producer, Topic.AI_TELEMETRY.value, df)
            telemetry_total += sent
            batch_index += 1
            print(
                f"[generator_podium] Produced "
                f"{telemetry_total}/{ai_count} ai_telemetry..."
            )

        print(
            f"[generator_podium] Summary: "
            f"{interaction_total} interaction_events, "
            f"{telemetry_total} ai_telemetry"
        )
    finally:
        await producer.stop()


def main() -> None:
    gen_config = GeneratorConfig.from_env()
    parser = argparse.ArgumentParser(
        description="Generate Podium synthetic data and stream to Redpanda"
    )
    parser.add_argument(
        "--rows", type=int, default=gen_config.default_rows,
        help=f"Number of interaction events to generate (default: {gen_config.default_rows})",
    )
    parser.add_argument(
        "--batch-size", type=int, default=gen_config.batch_size,
        help=f"Batch size for generation and Kafka production (default: {gen_config.batch_size})",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()
    asyncio.run(run(args.rows, args.batch_size, args.seed))


if __name__ == "__main__":
    main()
