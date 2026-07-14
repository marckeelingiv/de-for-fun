# Target Emulation Profiles

This document details the target enterprise profiles and execution scenarios that guide the Project Sandbox data stack.

---

## Target 1: Smith Entertainment Group (SEG)

### Profile Overview
* **Core Entity Focus:** Ryan Smith (Owner) & the executive operations team.
* **The Business Problem:** Orchestrating fragmented, high-velocity real-time event streams (concessions, ticketing, fan locations, player tracking) across multiple major sports franchises (Utah Jazz, Utah Mammoth) and a high-capacity physical arena (Delta Center).
* **The Simulation Scenario:** A sold-out event generating massive, concurrent spikes in transaction and location logs.
* **The Valuation Metric:** Millions of time-series event records generated per game, requiring ultra-low latency aggregation to optimize arena operations and dynamic revenue capture.

### Data Dimensions & Generation Profile
* **Scale:** ~30 million fan location pings per game event; ~500,000 POS transactions.
* **Frequency:** Location pings every 5 seconds per active device during the event window (4 hours). Transactions clustered around pre-game, quarters/intermissions, and post-game.
* **Key Use Cases:**
  * Real-time heatmaps of fan density for crowd control and concession staffing.
  * Real-time sales velocities per concession stand to trigger dynamic promotions or inventory adjustments.

---

## Target 2: Podium

### Profile Overview
* **Core Entity Focus:** Eric Rea, Denis Naydenov, and the product/platform engineering leadership.
* **The Business Problem:** Managing dense multi-tenant data structures tracking communication streams, review loops, and customer interactions across more than 50,000 distributed local businesses without performance degradation.
* **The Simulation Scenario:** High-volume event logs streaming text telemetry, automated AI conversational states, and merchant transaction conversions.
* **The Valuation Metric:** Massively scalable columnar indexing that provides instant local analytics to individual merchants while running aggregate platform-wide sentiment models.

### Data Dimensions & Generation Profile
* **Scale:** ~20 million interactions and telemetry events across 50,000 simulated merchant IDs.
* **Frequency:** Steady high-concurrency writes throughout business hours, with conversational telemetry containing varying token counts and sentiment scores.
* **Key Use Cases:**
  * Merchant-level response velocity metrics (SLA tracking).
  * Aggregate, real-time sentiment analysis and token consumption profiling for the platform-wide AI agents.
