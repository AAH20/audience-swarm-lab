# Benchmark protocol

## Claims and their evidence

| Output label | Required evidence | Permitted interpretation |
| --- | --- | --- |
| `SYNTHETIC_SCENARIO` | Frozen scenario, seed, code version, assumptions | Behavior inside the model |
| `HISTORICAL_BACKTEST` | Time-ordered holdout and source snapshot | Historical prediction error |
| `OFFLINE_POLICY_ESTIMATE` | Known propensities, overlap, logged outcomes | Estimated policy value under assumptions |
| `ONLINE_EXPERIMENT` | Random assignment, predeclared metric, sample-size plan | Measured causal effect for tested population |
| `PRODUCTION_OBSERVATION` | Live telemetry and data-quality checks | Observed association after deployment |

## Initial benchmark matrix

| Question | Baseline | Metrics | Failure signal |
| --- | --- | --- | --- |
| Does the swarm improve forecasts? | Static cohort rates and audience-twin | MAE, log loss, calibration by cohort | Complex model fails held-out baseline |
| Does GraphRAG improve grounding? | Current lexical retrieval and vector search | Citation precision, answer relevance, index/query cost | Uncited or temporally invalid assumptions |
| Does Jev improve decisions per dollar? | Deterministic policy and sampled LLM policy | Accuracy, Brier score, ECE, latency, cost | No gain after provider cost |
| Does matching improve business outcomes? | Popularity and margin ranking | Incremental contribution, retention, return rate | Engagement rises while margin falls |
| Are scenario effects stable? | Paired no-op and parameter sweeps | Sign stability, run spread, sensitivity | Sign flips under small plausible perturbations |
| Are costs controlled? | Explicit work and token budget | Cost per run, agent-step, successful decision | Unbounded provider calls |

Use the same information cutoff, dataset splits, and scoring rules for every comparator. Report negative results. Do not tune on a holdout and then describe it as unseen. For recommendation policy estimates, report effective sample size and reject insufficient overlap. A synthetic result cannot validate real audience behavior.

## Economics to measure

`scenario_cogs = graph_amortization + simulation_compute + provider_input + provider_output + storage + observability + human_review`.

`tenant_gross_margin = tenant_revenue - scenario_cogs - serving_cogs - allocated_support`.

The fixture's optional meter includes only CPU, graph allocation, storage/observability and an operating allowance. Jev/LLM and review are zero because they are **not called**, not because they would be free. Pricing should use p50 and p95 actual COGS, support burden, and retention from paying pilots rather than this synthetic fixture.
