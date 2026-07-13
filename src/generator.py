import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import argparse
import subprocess

from src.config import GeneratorConfig, ALL_TOPICS, RedpandaConfig
from src.generator_seg import run as run_seg
from src.generator_podium import run as run_podium


def ensure_topics_exist(brokers: str) -> None:
    for topic in ALL_TOPICS:
        try:
            subprocess.run(
                ["rpk", "topic", "create", topic, "--brokers", brokers],
                capture_output=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass


async def run(rows: int, batch_size: int, seed: int, domain: str) -> None:
    tasks = []
    if domain in ("seg", "both"):
        tasks.append(run_seg(rows, batch_size, seed))
    if domain in ("podium", "both"):
        tasks.append(run_podium(rows, batch_size, seed))
    if tasks:
        await asyncio.gather(*tasks)


def main() -> None:
    gen_config = GeneratorConfig.from_env()
    redpanda_config = RedpandaConfig.from_env()
    parser = argparse.ArgumentParser(
        description="Combined synthetic data generator (SEG + Podium)"
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=gen_config.default_rows,
        help=f"Number of rows to generate per domain (default: {gen_config.default_rows})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=gen_config.batch_size,
        help=f"Batch size for generation and Kafka production (default: {gen_config.batch_size})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--scale",
        choices=["full"],
        default=None,
        help="Run at full scale (50M rows). Overrides --rows.",
    )
    parser.add_argument(
        "--domain",
        choices=["seg", "podium", "both"],
        default="both",
        help="Which domain to generate (default: both)",
    )
    args = parser.parse_args()

    rows = gen_config.full_scale_rows if args.scale == "full" else args.rows
    batch_size = args.batch_size
    seed = args.seed
    domain = args.domain

    print("=== Combined Generator ===")
    print(f"  Rows: {rows:,} per domain")
    print(f"  Batch size: {batch_size:,}")
    print(f"  Seed: {seed}")
    print(f"  Domain: {domain}")
    print(f"  Redpanda brokers: {redpanda_config.brokers}")
    print()

    ensure_topics_exist(redpanda_config.brokers)

    asyncio.run(run(rows, batch_size, seed, domain))

    print()
    print("=== Combined Generation Complete ===")
    if domain in ("seg", "both"):
        print(f"  SEG: {rows:,} rows -> seg.fan-pings, seg.pos-transactions")
    if domain in ("podium", "both"):
        print(f"  Podium: {rows:,} rows -> podium.interaction-events, podium.ai-telemetry")


if __name__ == "__main__":
    main()
