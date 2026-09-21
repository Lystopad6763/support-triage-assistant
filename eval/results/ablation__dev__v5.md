# Ablation of v5 on dev

Each row is the prompt with ONE block removed. A block that costs nothing to remove is not doing the work its version claimed.

| variant | category | priority | next_step | all three | $/10k | chars |
|---|---|---|---|---|---|---|
| full | 76% | 74% | 70% | 46% | $9.48 | 7,023 |
| no_precedence | 62% | 74% | 62% | 30% (-16%) | $10.44 | 5,767 |
| no_priority_rules | 82% | 70% | 70% | 48% (+2%) | $10.44 | 6,245 |
| no_escalation_triggers | 72% | 74% | 26% | 20% (-26%) | $9.38 | 6,185 |
| no_routing_criteria | 74% | 72% | 72% | 46% (+0%) | $11.75 | 6,446 |

A negative delta means removing the block made it worse, so the block earns its place.
