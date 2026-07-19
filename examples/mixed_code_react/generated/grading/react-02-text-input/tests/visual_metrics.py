#!/usr/bin/env python3
"""Deterministic, content-aware metrics for screenshot comparison."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import numpy as np
from PIL import Image, ImageFilter


METRIC_VERSION = "visual-composite-v1"
DEFAULT_VISUAL_WEIGHTS = {
    "full_frame": 0.05,
    "foreground": 0.35,
    "edge": 0.35,
    "layout": 0.25,
}

_BACKGROUND_THRESHOLD = 16.0
_EDGE_THRESHOLD = 18.0


def _load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.float32)


def _border_background(image: np.ndarray) -> np.ndarray:
    """Estimate the page background from the median color along its border."""
    border = np.concatenate(
        (
            image[0, :, :],
            image[-1, :, :],
            image[:, 0, :],
            image[:, -1, :],
        ),
        axis=0,
    )
    return np.median(border, axis=0)


def _foreground_mask(image: np.ndarray) -> np.ndarray:
    background = _border_background(image)
    distance = np.max(np.abs(image - background), axis=2)
    return distance > _BACKGROUND_THRESHOLD


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask
    image = Image.fromarray(mask.astype(np.uint8) * 255)
    size = (radius * 2) + 1
    return np.asarray(image.filter(ImageFilter.MaxFilter(size=size))) > 0


def _edge_mask(image: np.ndarray) -> np.ndarray:
    gray = (
        (image[:, :, 0] * 0.299)
        + (image[:, :, 1] * 0.587)
        + (image[:, :, 2] * 0.114)
    )
    horizontal = np.zeros_like(gray)
    vertical = np.zeros_like(gray)
    horizontal[:, 1:] = np.abs(gray[:, 1:] - gray[:, :-1])
    vertical[1:, :] = np.abs(gray[1:, :] - gray[:-1, :])
    return np.maximum(horizontal, vertical) > _EDGE_THRESHOLD


def _full_frame_similarity(
    reference: np.ndarray,
    candidate: np.ndarray,
) -> float:
    difference = np.abs(reference - candidate).mean() / 255.0
    return float(np.clip(1.0 - difference, 0.0, 1.0))


def _foreground_similarity(
    reference: np.ndarray,
    candidate: np.ndarray,
    reference_mask: np.ndarray,
    candidate_mask: np.ndarray,
) -> float:
    comparison_region = _dilate(reference_mask | candidate_mask, radius=4)
    if not comparison_region.any():
        return 1.0
    difference = np.abs(reference - candidate).mean(axis=2) / 255.0
    return float(np.clip(1.0 - difference[comparison_region].mean(), 0.0, 1.0))


def _layout_similarity(
    reference_mask: np.ndarray,
    candidate_mask: np.ndarray,
) -> float:
    reference_region = _dilate(reference_mask, radius=3)
    candidate_region = _dilate(candidate_mask, radius=3)
    union = reference_region | candidate_region
    if not union.any():
        return 1.0
    intersection = reference_region & candidate_region
    return float(intersection.sum() / union.sum())


def _edge_similarity(reference: np.ndarray, candidate: np.ndarray) -> float:
    reference_edges = _edge_mask(reference)
    candidate_edges = _edge_mask(candidate)
    reference_count = int(reference_edges.sum())
    candidate_count = int(candidate_edges.sum())
    if reference_count == 0 and candidate_count == 0:
        return 1.0
    if reference_count == 0 or candidate_count == 0:
        return 0.0

    reference_matches = reference_edges & _dilate(candidate_edges, radius=2)
    candidate_matches = candidate_edges & _dilate(reference_edges, radius=2)
    recall = float(reference_matches.sum() / reference_count)
    precision = float(candidate_matches.sum() / candidate_count)
    if precision + recall == 0:
        return 0.0
    return float((2.0 * precision * recall) / (precision + recall))


def _normalized_weights(
    overrides: Mapping[str, float] | None,
) -> dict[str, float]:
    weights = dict(DEFAULT_VISUAL_WEIGHTS)
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


def visual_similarity(
    reference_path: Path,
    candidate_path: Path,
    weights: Mapping[str, float] | None = None,
) -> dict[str, float | bool]:
    """Return global and content-aware similarities plus a composite score."""
    reference = _load_rgb(reference_path)
    candidate = _load_rgb(candidate_path)
    if reference.shape != candidate.shape:
        return {
            "shape_match": False,
            "full_frame_similarity": 0.0,
            "foreground_similarity": 0.0,
            "edge_similarity": 0.0,
            "layout_similarity": 0.0,
            "composite_similarity": 0.0,
            "reference_foreground_fraction": 0.0,
            "candidate_foreground_fraction": 0.0,
        }

    reference_mask = _foreground_mask(reference)
    candidate_mask = _foreground_mask(candidate)
    metric_values = {
        "full_frame": _full_frame_similarity(reference, candidate),
        "foreground": _foreground_similarity(
            reference,
            candidate,
            reference_mask,
            candidate_mask,
        ),
        "edge": _edge_similarity(reference, candidate),
        "layout": _layout_similarity(reference_mask, candidate_mask),
    }
    normalized_weights = _normalized_weights(weights)
    composite = sum(
        metric_values[name] * normalized_weights[name]
        for name in normalized_weights
    )
    return {
        "shape_match": True,
        "full_frame_similarity": metric_values["full_frame"],
        "foreground_similarity": metric_values["foreground"],
        "edge_similarity": metric_values["edge"],
        "layout_similarity": metric_values["layout"],
        "composite_similarity": float(np.clip(composite, 0.0, 1.0)),
        "reference_foreground_fraction": float(reference_mask.mean()),
        "candidate_foreground_fraction": float(candidate_mask.mean()),
    }
