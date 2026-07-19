# Validate and normalize visual weights

normalized_weights(defaults, overrides=None) must copy defaults, reject unknown override names, reject negative values, require a positive total, and return weights normalized to sum to 1. Do not mutate either input mapping.
