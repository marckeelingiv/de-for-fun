# Persona Review System

## Decision Record

Build a personal, local-first review system that critiques mixed artifacts before they reach an audience. The first implementation is a set of version-controlled prompt specifications in this repository, not installed agent skills or an external service.

The system is advisory. It exposes tradeoffs and leaves decisions with the author.

## Objective

Reduce audience surprises in presentations, product/design work, code, and architecture by testing work against independent professional perspectives before external review.

## Review Domain

| Concept | Definition |
| --- | --- |
| Review brief | Required context: intended audience, goal, and requested decision or action. |
| Artifact | Submitted material, which may include slides, speaking notes, product documents, code, architecture, or a combination. |
| Persona | A bounded professional perspective with its own priorities, evidence standard, and critique rubric. |
| Panel | The set of personas selected or routed as relevant to a review. |
| Finding | A specific concern, strength, question, or recommendation supported by artifact evidence or clearly labeled assumptions. |
| Synthesis | A prioritized combined report that records consensus, disagreement, and author-owned decisions. |

## Default Personas

The initial panel contains one persona for each of these roles:

- CEO: strategy, business value, prioritization, decision clarity, and stakeholder impact.
- Marketing leader: audience, positioning, messaging, narrative, differentiation, and call to action.
- Data engineer: data contracts, quality, lineage, modeling, analytical correctness, and operating feasibility.
- Platform engineer: infrastructure, reliability, security, developer experience, and cost.
- Principal software engineer: architecture, technical risk, maintainability, delivery tradeoffs, and engineering clarity.

Personas are independent reviewers, not a simulated meeting. They may disagree and must not manufacture consensus.

## MVP Workflow

1. Author supplies an artifact and review brief containing the audience and goal.
2. The system routes relevant personas, while identifying roles with insufficient grounds to provide meaningful feedback.
3. Routed personas ask concise, targeted clarification questions.
4. The author responds once.
5. Each persona produces an independent critique within its role boundary.
6. A synthesizer produces a prioritized report in a total target time of 10 to 15 minutes.
7. The author decides what to change, accept, defer, or validate.

## Output Contract

Each persona report must include:

- Findings ordered by impact.
- Evidence from the artifact and review brief.
- Assumptions separately labeled from evidence.
- The consequence of leaving a material issue unresolved.
- A concrete recommended change or validation step.
- Questions that would materially change the conclusion.

The synthesis must include:

- The highest-priority changes before the artifact is shared.
- Consensus findings.
- Material disagreements, with each position and its tradeoff.
- Rehearsal questions or audience objections when relevant.
- Explicit decisions retained for the author; it must not claim authority to decide for them.

## Constraints

- Inputs may contain proprietary or customer-sensitive material.
- The first version must be local-first and make any external model use explicit.
- Persona definitions, rubrics, and output contracts must be reviewable and version-controlled.
- The system is optimized for practical feedback, not exhaustive diligence or quantitative scoring.

## Deliberate Non-Goals

- Replacing expert review, security review, legal review, or customer research.
- Simulating adversarial debates among personas.
- A hosted multi-user product in the first version.
- Treating all personas as equally relevant to every artifact.

## Open Implementation Decisions

- Prompt file format and directory layout.
- Artifact ingestion and redaction workflow for local-only material.
- Model/runtime used to execute persona reviews.
- Routing rules and the threshold for declaring a role irrelevant.
- Synthesis prompt and a repeatable evaluation set for measuring audience-surprise reduction.

## Initial Implementation

The first local implementation is in `reviews/` and `src/persona_review.py`.

1. Copy `reviews/brief_template.md` and complete the required audience, goal, and requested-decision sections.
2. Prepare a packet without transmitting material: `make persona-review BRIEF=path/to/brief.md ARTIFACT=path/to/artifact.md OUTPUT=reviews/output/review.md`.
3. Inspect the routed roles and packet before submitting any content to a model. Use `--roles` with `src/persona_review.py` to explicitly override routing when necessary.
4. Collect independent role reports and apply the synthesis instructions at the bottom of the generated packet.

The packet generator only reads local files and writes a local Markdown packet. It does not execute a model or make network requests.

For focused two-pass critiques in a new OpenCode session, see `docs/persona_conversations.md`.
