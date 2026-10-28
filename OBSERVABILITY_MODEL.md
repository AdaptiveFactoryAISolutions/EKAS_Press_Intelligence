# Observability model

`observability.model.assess` evaluates public engineering priors against the supplied signal IDs. Each catalog class exposes required observations, available observations and competitors. Every catalog pair has explicit required discriminators. A pair separates only when every required observation is available; unknown pair definitions remain unresolved.

Class states are FULLY_DISTINGUISHABLE, PARTIALLY_DISTINGUISHABLE, INDISTINGUISHABLE and NOT_OBSERVABLE. Class coverage is fully distinguishable classes / catalog classes. Pair coverage is separated pairs / all unordered catalog pairs. These are instrumentation capabilities, not diagnostic accuracy probabilities.

Unresolved groups are connected components of unresolved pair edges. Pairwise indistinguishability need not be transitive: inspect the returned exact edges before interpreting a group. The response explicitly documents this limitation.
