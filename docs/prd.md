# PRD: Project Sandbox (Decoupled Storage & Compute Data Stack)

## 1. Objective & Scope

The goal is to build a production-grade, local-first data engineering sandbox that simulates high-volume enterprise data workloads. The architecture decouples the storage layer from the compute layer by leveraging an S3-compatible object store (MinIO) as a data lakehouse. 

This allows absolute flexibility to run local analysis via DuckDB, exposed through a semantic layer to agentic AI workflows. The entire stack is deployed locally using a lightweight Kubernetes distribution (**k3s**).

---

## 2. Improved Technology Stack

To balance production-grade architectures with a lightweight local developer experience, we divide the tech stack as follows:

| Component | Local Development (Sandbox) | Production Reference | Rationale |
| :--- | :--- | :--- | :--- |
| **Storage Layer** | **MinIO** (deployed on k3s) | **AWS S3 / Cloud Storage** | S3 API compatibility; zero cloud costs during local dev; partitioned Parquet. |
| **Data Generation**| **Python + uv + Polars / PyArrow** | **Polars / Custom Worker Jobs** | Polars is single-node, multi-threaded, and blazingly fast with no JVM overhead. |
| **Compute Engines** | **DuckDB** | **DuckDB / MotherDuck / Athena** | **DuckDB** via `httpfs` for serverless local queries on the same Parquet files. |
| **Orchestration** | **Dagster** (deployed on k3s) | **Dagster Cloud / K8s** | Asset-based orchestration matches the flow from data generator -> storage -> dbt -> semantic layers. |
| **Transformation** | **dbt-core** with DuckDB adapter | **dbt-cloud / dbt-core** | Standardizes SQL-based modeling, documentation, and semantic layer definitions. |
| **BI & AI Semantic** | **Lightdash** & **Lightdash MCP Server** | **Lightdash Cloud** + AI Gateway | Lightdash reads dbt semantic definitions; MCP allows external LLMs to interact with metrics and data. |
| **Infrastructure** | **k3s** (Lightweight Kubernetes) | **Kubernetes (EKS/GKE)** | k3s provides a production-like Kubernetes API locally with minimal resource footprint. |

---

## 3. Storage Layer & Data Schema Specification

All raw and simulated event streams are persisted as immutable, partitioned **Apache Parquet** files. The S3 data lake uses a structured directory format to allow seamless partition pruning by the compute engines:
`s3://data-lakehouse/simulation_domain/tenant_id/year=YYYY/month=MM/`

### Domain A: Arena Telemetry (Smith Entertainment Group Simulation)

* **`fan_pings`**
  * `timestamp` (DateTime)
  * `device_id` (UUID)
  * `beacon_id` (String)
  * `x_coord` (Float64)
  * `y_coord` (Float64)
  * `estimated_dwell_time` (Int32)
* **`pos_transactions`**
  * `timestamp` (DateTime)
  * `transaction_id` (UUID)
  * `vendor_id` (String)
  * `item_id` (String)
  * `amount` (Decimal/Float64)
  * `payment_method` (String)

### Domain B: Merchant Interactions (Podium Simulation)

* **`interaction_events`**
  * `timestamp` (DateTime)
  * `merchant_id` (UUID)
  * `customer_id` (UUID)
  * `channel` (Enum: SMS, Web)
  * `direction` (Enum: Inbound, Outbound)
* **`ai_telemetry`**
  * `timestamp` (DateTime)
  * `interaction_id` (UUID)
  * `prompt_tokens` (Int32)
  * `completion_tokens` (Int32)
  * `sentiment_score` (Float64)
  * `latency_ms` (Int32)

---

## 4. Engineering & Execution Workflow

To maintain a clean, local-first developer experience, the entire toolchain must be scriptable and reproducible. Any engineer checking out the repository should be able to boot the entire stack solely via standard Python/uv scripts and Kubernetes manifests deployed to k3s.

### Step 1: Bootstrap Local Storage & Services
Use Kubernetes manifests (located in the `k3s/` directory) to deploy the services to your local k3s cluster:
* MinIO (S3-compatible storage with PVC, Service, and Deployment)
* DuckDB Shared Storage (PersistentVolumeClaim to store the shared `.db` files)
* Lightdash (Service and Deployment connected to DuckDB)
* Dagster (Service and Deployment for orchestration)

A lightweight bootstrapping Python script (managed via `uv run`) will run post-deployment to create the `data-lakehouse` bucket and set up standard access credentials.

### Step 2: Multi-threaded Synthetic Data Generation
Execute a high-performance Python script using `uv run`. 
* Uses **Polars** or **PyArrow** to generate 50M+ rows of hyper-realistic time-series data matching the schemas above.
* Streams partitioned Parquet files directly into the local MinIO bucket via `s3fs` or `boto3`.

### Step 3: Mount Compute Layers
* **DuckDB:** Query the files directly over HTTP using the `httpfs` extension:
  ```sql
  INSTALL httpfs;
  LOAD httpfs;
  SET s3_endpoint='localhost:9000';
  SET s3_use_ssl=false;
  SELECT * FROM read_parquet('s3://data-lakehouse/arena/**/*.parquet') LIMIT 10;
  ```

### Step 4: Run dbt Transformations & Dagster Pipelines
* Orchestrate data generation, MinIO verification, and dbt runs via a **Dagster** asset pipeline.
* Create dbt models that aggregate data into high-value operational metrics (e.g., arena bottleneck ratios, merchant response SLAs).

### Step 5: Expose AI Semantic Layer
* Define metrics inside dbt semantic layers (YAML metadata).
* Lightdash loads the dbt metadata and provides a UI.
* Run the custom Lightdash Model Context Protocol (MCP) server locally, enabling LLMs (such as Claude Code, Antigravity, or Aider) to safely inspect metrics schemas, run analytical queries, and generate visualizations via natural language commands.

---

## 5. Agentic AI & UI Experience

* **No Metric Hallucination:** By relying strictly on the dbt/Lightdash semantic definitions, LLMs interact with pre-vetted dimensions and measures (e.g., `total_revenue`, `average_dwell_time`) instead of writing raw SQL joins that could result in double-counting or schema errors.
* **Visual Presentation:** The visualization layer defaults to a dark-themed visual layout. Focus on minimal clutter, strong visual contrast, and high-density performance charts suitable for platform and operations executives.
