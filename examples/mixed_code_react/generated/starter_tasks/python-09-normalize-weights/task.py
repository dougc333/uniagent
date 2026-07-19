def normalized_weights(defaults: dict[str, float], overrides=None) -> dict[str, float]:
    defaults.update(overrides or {})
    return defaults
