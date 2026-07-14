# Continuous Data Generation — Design Questions

The current pipeline is a one-shot batch flow: `make generate` produces a fixed number of rows (default 100K) and exits, then `make buffer` drains Redpanda to MinIO Parquet and exits after 30s of idle. Everything is built around that "run once, done" lifecycle.

This document captures open design questions for switching to **continuous data generation** so you can watch data flow through the pipeline in real time. Answer as many as you can — "no preference" or "you decide" is a valid answer for any of them.

---

## 1. Overall Mode & Lifecycle

1. **What does "continuous" mean to you?** A docker container that runs forever and never exits untli a make command stoops it.

2. **New Make target vs. flag on existing one?** Use `make generate --continuous` (flag on the existing generator)

3. **Should `make buffer` also become long-running by default?** add a `--continuous` / `--no-idle-exit` flag

4. **Do you want a single command that launches both generator + buffer together** (e.g. `make stream` that starts both processes in the background), or do you prefer keeping them in separate terminals as they are today? YES

5. **Backfill-then-live:** start fresh with only live data from the moment you start the process

---

## 2. Throughput & Rate

6. **What rate of data generation do you want?** ~500 rows/sec

7. **Should the rate be configurable at runtime** `GENERATOR_RATE_ROWS_PER_SEC=500`.

8. **Should the rate vary over time to simulate bursts?** The current SEG generator has weighted POS time windows (pre-show, intermission, etc.). **simulate  bursts, such as intermission, and other events.** 

9. **Should different topics have different rates?** They should have different rates

10. **Batch size for Kafka production:** 500 rows every 2 seconds

---

## 3. Timestamps & Time Semantics

11. **This is the big one.** Today all timestamps are hardcoded: SEG data is pinned to July 12, 2025 (a single event night), and Podium data is spread across 2024 business days. For continuous generation, timestamps will use **wall-clock "now"** so each batch represents data that just happened. This directly affects the year/month partitioning in MinIO.

12. **If using "now" timestamps:** Should each record's timestamp be the actual current time

13. **Event-time vs. ingestion-time:** Do you want to track both a `event_time` (when the simulated event happened) and an `ingestion_time` (when it was produced to Kafka)? one timestamp column is sufficient

14. **Date progression for partitioning:** If the generator runs across midnight or month boundaries, new year/month partitions will appear in MinIO. That is the desire dbehaviour

15. **Should the SEG "event night" concept be preserved?** simulate aa new event every few hours of wall-clock time

---

## 4. Seed & Reproducibility

16. **Today the seed is fixed at 42 and each batch uses `seed + i * 7919`.** In continuous mode keep deterministic seeds (reproducible)

17. **If deterministic:** How should the seed advance across continuous cycles? Increment per-cycle

18. **Do you care about reproducibility at all for continuous mode**, yes. i care about reproducibility

---

## 5. DuckDB, dbt & Downstream Impact

19. **DuckDB views are registered once via `make mount`.** DuckDB views automatically see them (via glob)

20. **dbt models are currently full-refresh tables/views.** For continuous data, do you want to:
    - (b) Convert mart tables to **incremental** dbt models that only process new data?

21. **If incremental:** What's the incremental key / watermark? `timestamp` column? A batch ID? File modification time?
Use the max timestamp of the current table. 

22. **How often should dbt re-run in a continuous scenario?** On a Dagster schedule

23. **The MCP server loads the semantic manifest at import time** mcp sserver will use queries that hit the tables, so not an important question. 

---

## 6. Dagster Orchestration

24. **Should continuous generation be orchestrated by Dagster** should be a standalone process outside Dagster

25. **Today the `buffered_parquet` asset has a 120s timeout and intentionally allows `TimeoutExpired`.** In continuous mode, should stay as a subprocess

26. **Do you want a Dagster schedule that chains: generate → buffer → verify → dbt-run on a recurring interval?** Iprefer the generator/buffer running independently and Dagster only handling the dbt rebuild cycle

---

## 7. Data Cleanup & Retention

27. **Continuous generation will keep writing Parquet files to MinIO indefinitely.** this is a short-lived demo where disk usage doesn't matter

28. **Redpanda topic retention:** Retention policy of 1 hr

29. **Parquet file compaction:** Lets use redpanda to buffer messages for 15 minutes (4 files per hour) and then write to MinIO to reduce number of files

---

## 8. Schema & Data Model

30. **Do any schema changes need to accompany continuous mode?** add a `generated_at` column to distinguish batches from different continuous cycles. (dbt base models)

31. **Should the existing schemas stay exactly as-is** (same columns, same types), just with different timestamp behavior? YES

32. **Podium AI telemetry is currently 70% coverage of interactions** (generated after all interactions are produced). In continuous mode, should AI telemetry be generated alongside each interaction batch (simpler), or should we maintain the two-phase approach (collect interaction IDs, then sample 70% for telemetry)?
Lets keep it simple please

33. **Should we add any new tables or topics** work within the existing four (fan_pings, pos_transactions, interaction_events, ai_telemetry)?

---

## 9. Operational Concerns

34. **Graceful shutdown:** is it OK to drop the current partial batch?

35. **Health/status reporting:** per-batch prints like today is fine

36. **Reconnection behavior:** If Redpanda is briefly unavailable, should the generator then retry with backoff. then crash if failes after a while

37. **Should the generator be containerizable** Yes. run as a pod in the k3d cluster alongside Redpanda/MinIO

38. **Multiple generator instances:** one docker container per instance / business type

---

## 10. Scope & Priorities

39. **What's the primary goal?** Is this for a demo where you want to watch data appear in real time

40. **What's the minimum viable version** docker producing rows/sec with current timestamps, buffer runs forever, Dagster dbt run

41. **Is there a time budget for this work?** no budget

42. **Should this be documented as a new pipeline mode** YES. (updating AGENTS.md, Makefile help, README)

---

## Quick-Reference: Current Architecture

| Component | Current behavior | Continuous-mode question |
|-----------|-----------------|-------------------------|
| `generator.py` | One-shot, N rows, exits | Loop forever? |
| `buffer_writer.py` | Consumes until 30s idle, exits | Run indefinitely? |
| Timestamps | Hardcoded (July 2025 / 2024) | Use wall-clock now? |
| Seeds | Fixed (42) | Wall-clock or incremental? |
| dbt models | Full refresh | Incremental? Periodic re-run? |
| `make mount` | One-time view registration | Auto-refresh needed? |
| Dagster | One-shot asset materialization | Schedule/sensor? |
| MinIO | Accumulates files | Cleanup/compaction? |
| Redpanda | No retention policy | Set retention? |

---

*Answer whichever questions you have opinions on — I'll make reasonable defaults for the rest.*
