import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import json
import argparse
import random
import uuid
from datetime import datetime, timedelta

import polars as pl
from aiokafka import AIOKafkaProducer

from src.config import RedpandaConfig, Topic, GeneratorConfig

BEACON_COORDS: dict[str, tuple[float, float]] = {
    "entrance_north": (50.0, 95.0),
    "entrance_south": (50.0, 5.0),
    "food_court_a": (25.0, 50.0),
    "food_court_b": (75.0, 50.0),
    "concourse_main": (50.0, 50.0),
    "section_101": (20.0, 80.0),
    "section_102": (40.0, 80.0),
    "section_103": (60.0, 80.0),
    "section_104": (80.0, 80.0),
    "section_201": (20.0, 70.0),
    "section_202": (40.0, 70.0),
    "section_203": (60.0, 70.0),
    "section_204": (80.0, 70.0),
    "vip_lounge": (10.0, 90.0),
    "merch_store": (30.0, 60.0),
}

BEACON_DWELL_RANGES: dict[str, tuple[int, int]] = {
    "entrance_north": (5, 60),
    "entrance_south": (5, 60),
    "food_court_a": (30, 900),
    "food_court_b": (30, 900),
    "concourse_main": (10, 120),
    "section_101": (30, 900),
    "section_102": (30, 900),
    "section_103": (30, 900),
    "section_104": (30, 900),
    "section_201": (30, 900),
    "section_202": (30, 900),
    "section_203": (30, 900),
    "section_204": (30, 900),
    "vip_lounge": (30, 900),
    "merch_store": (30, 300),
}

VENDOR_ITEMS: dict[str, list[str]] = {
    "merch_001": ["tshirt", "hoodie", "cap"],
    "merch_002": ["jersey", "scarf", "hat"],
    "concession_001": ["hotdog", "nachos", "popcorn"],
    "concession_002": ["burger", "fries", "soda"],
    "concession_003": ["pizza", "wings", "nachos"],
    "bar_001": ["beer", "wine", "cocktail"],
    "bar_002": ["beer", "wine", "cocktail"],
    "vip_bar_001": ["champagne", "cocktail", "wine"],
}

ITEM_PRICE_RANGES: dict[str, tuple[float, float]] = {
    "tshirt": (35.0, 55.0),
    "hoodie": (55.0, 85.0),
    "cap": (20.0, 35.0),
    "jersey": (100.0, 150.0),
    "scarf": (15.0, 30.0),
    "hat": (20.0, 35.0),
    "hotdog": (6.0, 9.0),
    "nachos": (7.0, 11.0),
    "popcorn": (6.0, 10.0),
    "burger": (10.0, 15.0),
    "fries": (5.0, 8.0),
    "soda": (4.0, 7.0),
    "pizza": (8.0, 13.0),
    "wings": (9.0, 14.0),
    "beer": (8.0, 14.0),
    "wine": (9.0, 16.0),
    "cocktail": (12.0, 20.0),
    "champagne": (25.0, 80.0),
}

PAYMENT_METHODS: list[str] = ["credit_card", "mobile_pay", "cash"]
PAYMENT_WEIGHTS: list[float] = [0.50, 0.35, 0.15]

DEVICE_POOL_SIZE = 5000
EVENT_NIGHT_BASE = datetime(2025, 7, 12, 18, 0, 0)
EVENT_NIGHT_END = datetime(2025, 7, 12, 23, 0, 0)
EVENT_NIGHT_SECONDS = int((EVENT_NIGHT_END - EVENT_NIGHT_BASE).total_seconds())

POS_TIME_WINDOWS: list[tuple[datetime, datetime, float]] = [
    (datetime(2025, 7, 12, 18, 0, 0), datetime(2025, 7, 12, 19, 0, 0), 0.40),
    (datetime(2025, 7, 12, 19, 0, 0), datetime(2025, 7, 12, 20, 0, 0), 0.15),
    (datetime(2025, 7, 12, 20, 0, 0), datetime(2025, 7, 12, 21, 0, 0), 0.10),
    (datetime(2025, 7, 12, 21, 0, 0), datetime(2025, 7, 12, 21, 30, 0), 0.25),
    (datetime(2025, 7, 12, 21, 30, 0), datetime(2025, 7, 12, 23, 0, 0), 0.10),
]


def _generate_device_pool(size: int, rng: random.Random) -> list[str]:
    return [str(uuid.UUID(int=rng.getrandbits(128), version=4)) for _ in range(size)]


def generate_fan_pings(num_rows: int, seed: int) -> pl.DataFrame:
    pool_rng = random.Random(seed)
    device_pool = _generate_device_pool(DEVICE_POOL_SIZE, pool_rng)

    rng = random.Random(seed + 1)
    beacons = list(BEACON_COORDS.keys())

    device_ids = rng.choices(device_pool, k=num_rows)
    beacon_ids = rng.choices(beacons, k=num_rows)

    timestamps: list[datetime] = []
    x_coords: list[float] = []
    y_coords: list[float] = []
    dwell_times: list[int] = []

    for i in range(num_rows):
        offset = rng.randint(0, EVENT_NIGHT_SECONDS)
        timestamps.append(EVENT_NIGHT_BASE + timedelta(seconds=offset))

        beacon = beacon_ids[i]
        bx, by = BEACON_COORDS[beacon]
        x = bx + rng.gauss(0.0, 3.0)
        y = by + rng.gauss(0.0, 3.0)
        x_coords.append(max(0.0, min(100.0, x)))
        y_coords.append(max(0.0, min(100.0, y)))

        lo, hi = BEACON_DWELL_RANGES[beacon]
        dwell_times.append(rng.randint(lo, hi))

    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "device_id": device_ids,
            "beacon_id": beacon_ids,
            "x_coord": x_coords,
            "y_coord": y_coords,
            "estimated_dwell_time": dwell_times,
        },
        schema={
            "timestamp": pl.Datetime,
            "device_id": pl.Utf8,
            "beacon_id": pl.Utf8,
            "x_coord": pl.Float64,
            "y_coord": pl.Float64,
            "estimated_dwell_time": pl.Int32,
        },
    )


def generate_pos_transactions(num_rows: int, seed: int) -> pl.DataFrame:
    rng = random.Random(seed)
    vendors = list(VENDOR_ITEMS.keys())
    window_starts = [w[0] for w in POS_TIME_WINDOWS]
    window_durations = [int((w[1] - w[0]).total_seconds()) for w in POS_TIME_WINDOWS]
    window_weights = [w[2] for w in POS_TIME_WINDOWS]

    timestamps: list[datetime] = []
    transaction_ids: list[str] = []
    vendor_ids: list[str] = []
    item_ids: list[str] = []
    amounts: list[float] = []
    payment_methods: list[str] = []

    for _ in range(num_rows):
        window_idx = rng.choices(range(len(POS_TIME_WINDOWS)), weights=window_weights, k=1)[0]
        offset = rng.randint(0, window_durations[window_idx])
        timestamps.append(window_starts[window_idx] + timedelta(seconds=offset))

        transaction_ids.append(str(uuid.UUID(int=rng.getrandbits(128), version=4)))

        vendor = rng.choice(vendors)
        vendor_ids.append(vendor)

        item = rng.choice(VENDOR_ITEMS[vendor])
        item_ids.append(item)

        lo, hi = ITEM_PRICE_RANGES[item]
        amounts.append(round(rng.uniform(lo, hi), 2))

        payment_methods.append(rng.choices(PAYMENT_METHODS, weights=PAYMENT_WEIGHTS, k=1)[0])

    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "transaction_id": transaction_ids,
            "vendor_id": vendor_ids,
            "item_id": item_ids,
            "amount": amounts,
            "payment_method": payment_methods,
        },
        schema={
            "timestamp": pl.Datetime,
            "transaction_id": pl.Utf8,
            "vendor_id": pl.Utf8,
            "item_id": pl.Utf8,
            "amount": pl.Float64,
            "payment_method": pl.Utf8,
        },
    )


async def produce_to_kafka(producer: AIOKafkaProducer, topic: str, df: pl.DataFrame) -> int:
    count = 0
    for row in df.iter_rows(named=True):
        record: dict[str, object] = {}
        for key, value in row.items():
            if isinstance(value, datetime):
                record[key] = value.isoformat()
            else:
                record[key] = value
        await producer.send_and_wait(topic, value=json.dumps(record).encode("utf-8"))
        count += 1
    return count


async def run(rows: int, batch_size: int, seed: int) -> None:
    redpanda_config = RedpandaConfig.from_env()
    producer = AIOKafkaProducer(bootstrap_servers=redpanda_config.brokers)
    await producer.start()
    fan_pings_total = 0
    pos_total = 0
    try:
        num_batches = (rows + batch_size - 1) // batch_size
        for i in range(num_batches):
            current_batch_size = min(batch_size, rows - i * batch_size)
            batch_seed = seed + i * 7919

            fan_df = generate_fan_pings(current_batch_size, batch_seed)
            fan_count = await produce_to_kafka(producer, Topic.FAN_PINGS.value, fan_df)
            fan_pings_total += fan_count
            print(f"[generator_seg] Produced {fan_pings_total}/{rows} fan_pings events...")

            pos_df = generate_pos_transactions(current_batch_size, batch_seed + 1)
            pos_count = await produce_to_kafka(producer, Topic.POS_TRANSACTIONS.value, pos_df)
            pos_total += pos_count
            print(f"[generator_seg] Produced {pos_total}/{rows} pos_transactions events...")
    finally:
        await producer.stop()

    print(f"\n[generator_seg] Summary: fan_pings={fan_pings_total}, pos_transactions={pos_total}")


def main():
    gen_config = GeneratorConfig.from_env()
    parser = argparse.ArgumentParser(description="SEG synthetic data generator")
    parser.add_argument("--rows", type=int, default=gen_config.default_rows)
    parser.add_argument("--batch-size", type=int, default=gen_config.batch_size)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    asyncio.run(run(args.rows, args.batch_size, args.seed))


if __name__ == "__main__":
    main()
