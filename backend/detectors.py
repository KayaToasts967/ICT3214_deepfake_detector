"""Team-owned models plug in here. No detector is silently substituted."""
import importlib
import math
import os
from typing import Protocol

import numpy as np


class Detector(Protocol):
    name: str
    version: str

    def predict(self, samples: np.ndarray, sample_rate: int) -> dict:
        """Return synthetic_score in [0, 1] and optional evidence: list[str]."""


def load_plugin(spec: str):
    module, separator, factory = spec.partition(":")
    if not separator or not module or not factory:
        raise ValueError("Plugin must be module_name:factory_name")
    return getattr(importlib.import_module(module), factory)()


def load_detector():
    spec = os.getenv("DETECTOR_PLUGIN", "")
    return load_plugin(spec) if spec else None


def validate_prediction(value: dict) -> dict:
    if not isinstance(value, dict) or isinstance(value.get("synthetic_score"), bool):
        raise ValueError("Detector must return a dict with a numeric synthetic_score")
    score = float(value["synthetic_score"])
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError("Detector synthetic_score must be finite and between 0 and 1")
    evidence = value.get("evidence", [])
    if not isinstance(evidence, list) or any(not isinstance(v, str) for v in evidence):
        raise ValueError("Detector evidence must be a list of strings")
    return {"synthetic_score": score, "evidence": [v[:500] for v in evidence[:8]]}


class DemoDetector:
    name = "Demonstration fixture"
    version = "fixture-1"

    def __init__(self):
        self.index = 0

    def predict(self, samples, sample_rate):
        # Deliberately independent of the audio. This is UI/integration test data.
        pattern = [0.12, 0.21, 0.38, 0.79, 0.91, 0.86, 0.46, 0.18]
        score = pattern[self.index % len(pattern)]
        self.index += 1
        return {"synthetic_score": score, "evidence": [
            "Simulated score for testing the report interface; no trained detector evaluated this audio."
        ]}
