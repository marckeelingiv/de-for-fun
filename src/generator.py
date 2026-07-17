import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
import argparse
import subprocess
from dataclasses import replace

from src.config import GeneratorConfig, ALL_TOPICS, RedpandaConfig, ContinuousGeneratorConfig
from src.generator_seg import run as run_seg
from src.generator_podium import run as run_podium
from src.generator_seg import run_continuous as run_seg_continuous
from src.generator_podium import run_continuous as run_podium_continuous


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


async def run_continuous(config: ContinuousGeneratorConfig, seed: int, domain: str) -> None:
    tasks = []
    if domain in ("seg", "both"):
        tasks.append(run_seg_continuous(config, seed))
    if domain in ("podium", "both"):
        tasks.append(run_podium_continuous(config, seed + 100000))
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
    parser.add_argument(
        "--continuous",
        action="store_true",
        default=False,
        help="Run in continuous mode (infinite generation loop). Overrides --rows and --scale.",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=None,
        help="Rows per second in continuous mode (overrides GENERATOR_RATE_ROWS_PER_SEC env var).",
    )
    args = parser.parse_args()

    if args.continuous:
        cont_config = ContinuousGeneratorConfig.from_env()
        if args.rate is not None:
            cont_config = replace(cont_config, rows_per_sec=args.rate)

        seed = args.seed
        domain = args.domain

        print("=== Continuous Generator ===")
        print(f"  Rate: {cont_config.rows_per_sec} rows/sec")
        print(f"  Batch interval: {cont_config.batch_interval_sec}s")
        print(f"  Batch size: {cont_config.batch_size} rows/batch")
        print(f"  SEG event cycle: {cont_config.seg_event_cycle_hours}h")
        print(f"  Topic weights: {cont_config.topic_weights}")
        print(f"  Seed: {seed}")
        print(f"  Domain: {domain}")
        print(f"  Redpanda brokers: {redpanda_config.brokers}")
        print()

        ensure_topics_exist(redpanda_config.brokers)

        asyncio.run(run_continuous(cont_config, seed, domain))

        print()
        print("=== Continuous Generation Stopped ===")
        return

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
