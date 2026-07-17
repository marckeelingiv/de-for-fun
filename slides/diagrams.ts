export const diagrams: Record<string, string> = {
  architecture: `
flowchart LR
  subgraph Ingestion[Simulation and Buffering]
    Gen[Python and Polars generators]
    RP[(Redpanda topics)]
    Buffer[Buffer writer]
  end

  subgraph Lake[Object Storage]
    MinIO[(MinIO)]
    Parquet[Partitioned Parquet]
  end

  subgraph Compute[Transform and Orchestrate]
    Duck[DuckDB httpfs]
    DBT[dbt models]
    Dagster[Dagster assets]
  end

  subgraph Semantic[BI and AI]
    Lightdash[Lightdash]
    MCP[MCP server]
    LLM[LLM client]
  end

  Gen -->|JSON events| RP
  RP -->|consume batches| Buffer
  Buffer -->|write Parquet| MinIO
  MinIO --> Parquet
  Duck -->|scan over S3 API| Parquet
  DBT -->|build marts| Duck
  Dagster -->|coordinate| DBT
  Lightdash -->|semantic project| DBT
  MCP -->|semantic manifest + DuckDB| DBT
  LLM -->|tool calls| MCP
`,

  streams: `
sequenceDiagram
  participant SEG as SEG Generator
  participant Podium as Podium Generator
  participant RP as Redpanda
  participant Buffer as Buffer Writer
  participant MinIO as MinIO Lakehouse
  participant Duck as DuckDB

  SEG->>RP: seg.fan-pings
  SEG->>RP: seg.pos-transactions
  Podium->>RP: podium.interaction-events
  Podium->>RP: podium.ai-telemetry
  RP->>Buffer: topic batches
  Buffer->>MinIO: domain/table/tenant_id/year/month/*.parquet
  Duck->>MinIO: httpfs glob scan
`,

  dbtLineage: `
flowchart TB
  fan[base_fan_pings] --> stgFan[stg_fan_pings]
  pos[base_pos_transactions] --> stgPos[stg_pos_transactions]
  int[base_interaction_events] --> stgInt[stg_interaction_events]
  ai[base_ai_telemetry] --> stgAi[stg_ai_telemetry]

  stgFan --> arena[mtt_arena_bottlenecks]
  stgPos --> pricing[mtt_dynamic_pricing]
  stgInt --> sentiment[mtt_merchant_sentiment]
  stgAi --> sentiment
  stgAi --> slas[mtt_ai_slas]

  arena --> sem[semantic_models.yml]
  pricing --> sem
  sentiment --> sem
  slas --> sem
  sem --> metrics[metrics.yml]
  metrics --> mcp[MCP tools]
`,

  mcp: `
flowchart LR
  User[Presenter asks a metric question]
  LLM[LLM client]
  MCP[MCP server]
  Manifest[semantic_manifest.json]
  SQL[Generated bounded SQL]
  Duck[(DuckDB dev.duckdb)]
  Chart[Dark themed PNG chart]

  User --> LLM
  LLM -->|list_metrics| getList[MCP tool]
  LLM -->|query_metric| MCP
  MCP --> Manifest
  MCP --> SQL
  SQL --> Duck
  MCP --> Chart
`,
}
