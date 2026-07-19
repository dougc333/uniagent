def normalized_weights(
    defaults: dict[str, float],
    overrides: dict[str, float] | None = None,
) -> dict[str, float]:
    weights = {name: float(value) for name, value in defaults.items()}
    if overrides:
        unknown = set(overrides) - set(weights)
        if unknown:
            raise ValueError(f"Unknown visual metric weights: {sorted(unknown)}")
        weights.update({name: float(value) for name, value in overrides.items()})
    if any(value < 0 for value in weights.values()):
        raise ValueError("Visual metric weights must be non-negative")
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("At least one visual metric weight must be positive")
    return {name: value / total for name, value in weights.items()}
