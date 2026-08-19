# Persona Conversations

Use a persona conversation when you want a focused, two-pass critique from one professional perspective. The command launches the OpenCode TUI with a prompt that loads the review contract, selected persona, review brief, and one artifact from local paths.

For a combined panel packet, use `make persona-review` instead. The conversation launcher does not create a panel synthesis.

## Prerequisites

- OpenCode is installed and has a configured model.
- A review brief includes non-empty `Audience`, `Goal`, and `Requested Decision or Action` sections. Start with `reviews/brief_template.md`.
- The artifact is a local file. OpenCode determines which file types it can inspect.

## Start A Conversation

```bash
make persona-conversation \
  PERSONA=ceo \
  BRIEF=reviews/briefs/warehouse_proposal.md \
  ARTIFACT=docs/prd.md
```

The command starts a new interactive session. The persona begins by asking up to five clarification questions. Answer them in the session, then ask it to complete its independent critique using the loaded contract.

Available `PERSONA` values:

- `ceo`
- `marketing_leader`
- `data_engineer`
- `platform_engineer`
- `principal_software_engineer`

## Examples

### Rehearse An Executive Presentation

```bash
make persona-conversation \
  PERSONA=ceo \
  BRIEF=reviews/briefs/q3_investment.md \
  ARTIFACT=slides/q3_investment.pdf
```

Use this to test whether an executive audience can understand the decision, business value, tradeoffs, and action requested.

### Challenge Product Positioning

```bash
make persona-conversation \
  PERSONA=marketing_leader \
  BRIEF=reviews/briefs/feature_launch.md \
  ARTIFACT=docs/feature_launch.md
```

Use this to test audience fit, central message, proof for claims, differentiation, and the call to action.

### Review A Data Design

```bash
make persona-conversation \
  PERSONA=data_engineer \
  BRIEF=reviews/briefs/metric_definition.md \
  ARTIFACT=dbt_project/models/marts/seg/mtt_dynamic_pricing.sql
```

Use this to examine contracts, metric correctness, lineage, freshness, and validation gaps.

### Review A Platform Change

```bash
make persona-conversation \
  PERSONA=platform_engineer \
  BRIEF=reviews/briefs/trino_deployment.md \
  ARTIFACT=k3s/trino.yaml
```

Use this to examine reliability, security, capacity, deployment, and operational ownership.

### Review Architecture

```bash
make persona-conversation \
  PERSONA=principal_software_engineer \
  BRIEF=reviews/briefs/mcp_design.md \
  ARTIFACT=src/mcp_server.py
```

Use this to assess interfaces, technical risk, alternatives, delivery sequencing, and testability.

## Panel Workflow

Run independent conversations for the roles that matter, saving each critique locally. Then create a packet for a synthesis session:

```bash
make persona-review \
  BRIEF=reviews/briefs/warehouse_proposal.md \
  ARTIFACT=docs/prd.md \
  OUTPUT=reviews/output/warehouse_proposal_packet.md
```

Start a separate OpenCode session with the packet attached and ask it to follow the `Synthesis Instructions` at the bottom. Keep the final decision with the author.

## Data Handling

The launcher starts OpenCode and gives it local file paths to read. It does not call a model directly. The active OpenCode provider receives material read in the session according to its own configuration and policies; inspect the files before launching a session containing sensitive material.
