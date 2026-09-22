# Architecture and implementation gates

The long-term product is an audience decision laboratory, not a “predict anything” engine. Simulation is for hypothesis generation and stress testing. Recommendation lift must be demonstrated with consented outcomes and controlled experiments. Version 0.1 implements the shaded reference path below; the remaining components are planned interfaces, not live integrations.

## System planes

```mermaid
flowchart TB
  subgraph Source[Permissioned sources]
    Events[Consented events and exposure logs]
    Catalog[Versioned products, cost and inventory]
    Research[Licensed research and feedback]
  end
  subgraph Lake[Proposed lakehouse]
    Ingest[Event contracts and deletion propagation]
    Bronze[Iceberg Bronze source records]
    Silver[Iceberg Silver normalized records]
    Gold[Iceberg Gold point-in-time features]
  end
  subgraph Context[Context plane]
    Lexical[Implemented lexical retrieval]
    Graph[Proposed GraphRAG index]
    Compiler[Scenario compiler and assumption review]
  end
  subgraph World[Experiment plane]
    Agents[Implemented synthetic segments]
    Social[Implemented social graph]
    Runner[Implemented paired experiment runner]
    Jev[Proposed Jev decision adapter]
    LLM[Proposed selective LLM agents]
  end
  subgraph Decision[Recommendation plane]
    Rank[Implemented heuristic ranking]
    OPE[Implemented logged-policy estimate]
    Service[Proposed low-latency serving API]
    Test[Proposed randomized online test]
  end
  subgraph Evidence[Evidence plane]
    Receipts[Proposed Agent Trust Fabric bridge]
    GRC[Proposed GRC_Claw bridge]
  end
  Events --> Ingest --> Bronze --> Silver --> Gold
  Catalog --> Ingest
  Research --> Lexical --> Compiler
  Research -. planned .-> Graph -. planned .-> Compiler
  Gold -. planned .-> Compiler
  Compiler --> Agents --> Runner
  Compiler --> Social --> Runner
  Jev -. planned .-> Runner
  LLM -. planned .-> Runner
  Gold -. planned .-> Rank
  Rank --> OPE
  Rank -. planned .-> Service -. planned .-> Test
  Test -. planned .-> Gold
  Runner -. planned .-> Receipts -. planned .-> GRC
  Test -. planned .-> Receipts
```

**Version 0.1:** The JSON scenario is validated, a source-aware lexical control arm returns citations, synthetic agents are sampled by segment, and all arms share the same draw stream per run. Each agent can purchase one of multiple competing products or nothing. Peer ownership affects next-step utility. The output includes product counts, adoption trajectories, gross contribution, marketing cost, net contribution, paired effects and an illustrative cost estimate.

The included SQLite BI reference ingests result JSON idempotently by scenario digest and exposes arm-level net contribution and paired effects. It rejects results labeled as anything other than synthetic. It demonstrates the result contract and repeatable reporting on one machine; it is not a distributed, continuously ingesting Iceberg implementation.

**Intended data plane:** Each observed event should carry tenant, pseudonymous subject, event time, ingest time, consent purpose, source, product, event type and schema version. Exposure events also need candidate set, chosen order, policy version and selection propensity. Product snapshots need effective time, price, unit cost, inventory and eligibility. Iceberg snapshots should fix the data state used for backtests and support deletion propagation. No production data plane exists in this release.

**Intended context plane:** Preserve document owner, license, valid time, source ID, content hash and citation span. A scenario compiler should present extracted assumptions and conflicting evidence for review before freezing a run. The current BM25 retrieval is a baseline; it does not infer facts, build a graph, or validate claims.

**Intended agent-policy interface:** `decide(state, candidates, budget) -> choice, probabilities, model_version, usage`. The deterministic reference model remains a control arm. A Jev adapter would handle bounded typed questions, while selective generative policies would handle a small number of complex turns. Provider outputs never authorize real-world actions by themselves. The current reference engine does not call either provider.

## Scenario lifecycle

```mermaid
sequenceDiagram
  participant Analyst
  participant Validator
  participant Context
  participant Runner
  participant Evaluator
  participant Evidence
  Analyst->>Validator: Submit versioned scenario
  Validator-->>Analyst: Contract and work-budget result
  Validator->>Context: Retrieve supporting synthetic documents
  Context-->>Analyst: Source, license and excerpts
  Analyst->>Runner: Launch baseline and interventions
  loop Every seed and step
    Runner->>Runner: Apply common draws and synchronous transitions
  end
  Runner->>Evaluator: Arm outcomes and per-run pairs
  Evaluator-->>Analyst: Distributions, paired effects and cost
  Evaluator-->>Evidence: Proposed receipt export
```

## Recommendation path

```mermaid
flowchart LR
  Request[Consented request] --> Eligible[Purpose, inventory and eligibility]
  Eligible --> Candidates[Content, graph and collaborative candidates]
  Candidates --> Features[Point-in-time features]
  Features --> Predict[Conversion, return and retention models]
  Predict --> Calibrate[Calibration and uncertainty]
  Calibrate --> Rank[Incremental-value constrained rerank]
  Rank --> Explore[Bounded exploration]
  Explore --> Serve[Recommendation and reason codes]
  Serve --> Log[Exposure plus logging propensity]
  Log --> Outcome[Delayed purchases, returns and retention]
  Outcome --> Evaluate[Offline and online evaluation]
  Evaluate --> Predict
```

Only a segment-level heuristic ranking and a self-normalized inverse-propensity evaluator are implemented. The serving API, calibrated models, uplift models, candidate indexes, exploration and online experiment service remain milestones. Synthetic labels must not be treated as production ground truth.

## Public contracts to freeze next

| Entity | Required fields | Invariant |
| --- | --- | --- |
| `ScenarioManifest` | scenario ID, data cutoff, source snapshot IDs, products, interventions, seeds, model versions, budget | Frozen before scoring |
| `EvidenceSource` | source ID, owner, license, valid time, digest, citation span | Every external assumption traceable |
| `ObservedEvent` | pseudonymous subject, consent purpose, event time, ingest time, product, event, schema version | No future leakage into past features |
| `Exposure` | context, candidate set, selected action, policy version, propensity | Positive known propensity for off-policy scoring |
| `Outcome` | exposure ID, observation window, purchase, return, retention, margin | Delayed outcomes linked to exposure |
| `AgentDecision` | run ID, agent ID, step, state digest, alternatives, choice, usage | Reproducible or explicitly stochastic |
| `ExperimentResult` | arm, metric, seeds, paired effects, run quantiles, evidence label | Synthetic and measured outputs never conflated |

## Release gates

1. **Reference engine:** deterministic replay, no-op arm exactly zero, bounded work, synthetic fixture, local BI ingestion, CI. Implemented.
2. **Evidence-grounded scenarios:** licensed-source ingestion, temporal cutoff, GraphRAG adapter, citation span tests and human assumption review.
3. **Hybrid swarm:** versioned policy interface, Jev/LLM adapters, model-call budget, fallbacks, trace capture and comparison with deterministic control.
4. **Observed-data validation:** consented datasets, point-in-time joins, time-split holdouts, calibration, naive and audience-twin baselines.
5. **Matching pilot:** eligibility, candidate retrieval, calibrated ranking, propensity logging, offline policy evaluation and randomized online test.
6. **Governed operations:** authenticated source receipts, tenant isolation, deletion tests, monitoring, incident response and GRC_Claw mapping.

The intended commercial layer is hosted connectors, managed private data, scalable experiment scheduling, enterprise controls, validated domain packs and support. The OSS layer keeps contracts, reference engine, evaluation methods, synthetic fixtures, and cost-meter formulas inspectable. Any “better than MiroFish” or “better than social platforms” claim requires task-specific external evidence under the benchmark protocol.
