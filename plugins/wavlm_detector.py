"""VoiceScope detector adapter for the WavLM fake/real model trained in the notebook.

Expects the trained model saved to  models/wavlm-deepfake-detector/
(trainer.save_model(...) + feature_extractor.save_pretrained(...) in Colab).
"""
import os
from pathlib import Path

import numpy as np
import torch
from transformers import Wav2Vec2FeatureExtractor, WavLMForSequenceClassification

MODEL_SUBDIR = "wavlm-deepfake-detector"
SAMPLING_RATE = 16000
CLIP_SECONDS = 2  # the model was trained on 2-second FoR clips


class WavLMDetector:
    name = "WavLM deepfake voice detector"

    def __init__(self):
        model_path = Path(os.environ.get("MODEL_DIR", "models")) / MODEL_SUBDIR
        if not model_path.exists():
            raise FileNotFoundError(f"Trained model not found at {model_path}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_path)
        self.model = WavLMForSequenceClassification.from_pretrained(model_path).to(self.device)
        self.model.eval()
        label2id = {v.lower(): int(k) for k, v in self.model.config.id2label.items()}
        if "fake" not in label2id:
            raise ValueError(f"Model labels must include 'fake': {self.model.config.id2label}")
        self.fake_id = label2id["fake"]
        self.version = model_path.name

    def _p_fake(self, clip):
        max_len = SAMPLING_RATE * CLIP_SECONDS
        inputs = self.feature_extractor(
            clip, sampling_rate=SAMPLING_RATE, return_tensors="pt",
            max_length=max_len, truncation=True, padding="max_length",
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.inference_mode():
            probs = self.model(**inputs).logits.softmax(-1)[0].cpu().numpy()
        return float(probs[self.fake_id])

    def predict(self, samples, sample_rate):
        # VoiceScope sends 2-4 s windows; the model expects 2 s, so score each
        # 2 s piece and average (same idea as the notebook's video chunking).
        samples = np.asarray(samples, dtype=np.float32)
        size = SAMPLING_RATE * CLIP_SECONDS
        pieces = [samples[i:i + size] for i in range(0, len(samples), size)]
        pieces = [p for p in pieces if len(p) >= SAMPLING_RATE * 0.5] or [samples]
        scores = [self._p_fake(p) for p in pieces]
        return {"synthetic_score": float(min(1.0, max(0.0, np.mean(scores)))), "evidence": []}


def create_detector():
    return WavLMDetector()
