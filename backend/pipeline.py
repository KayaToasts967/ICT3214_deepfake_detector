"""Media normalization, overlapping windows, and transparent aggregation."""
import os
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np

from .detectors import validate_prediction

SAMPLE_RATE = 16000
WINDOW_SECONDS = 4.0
HOP_SECONDS = 2.0
LOW_THRESHOLD = 0.35
HIGH_THRESHOLD = 0.65
MAX_DURATION = 600
MIN_DURATION = 2
ENERGY_FLOOR = 0.003  # RMS energy screen, NOT a voice activity detector.


class MediaError(Exception):
    pass


def ffmpeg_executable():
    explicit = os.getenv("FFMPEG_BINARY")
    if explicit:
        return explicit
    system = shutil.which("ffmpeg")
    if system:
        return system
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def normalize_media(source: Path, target: Path) -> np.ndarray:
    command = [ffmpeg_executable(), "-nostdin", "-hide_banner", "-loglevel", "error",
               "-protocol_whitelist", "file,pipe", "-i", str(source), "-map", "0:a:0",
               "-vn", "-sn", "-dn", "-t", str(MAX_DURATION + 0.25),
               "-ac", "1", "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le",
               "-y", str(target)]
    try:
        decoded = subprocess.run(command, capture_output=True, timeout=120,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as exc:
        raise MediaError("Audio decoding timed out. Try a shorter recording.") from exc
    except OSError as exc:
        raise MediaError("FFmpeg could not start. Check the server's FFmpeg installation.") from exc
    if decoded.returncode != 0:
        raise MediaError("Cannot decode an audio track. The file may be damaged, unsupported, or a video without audio.")
    try:
        with wave.open(str(target), "rb") as wav:
            samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32) / 32768
    except (OSError, wave.Error) as exc:
        raise MediaError("Decoded audio could not be read.") from exc
    duration = len(samples) / SAMPLE_RATE
    if duration > MAX_DURATION:
        raise MediaError("Recording exceeds the 10-minute limit. Trim it before uploading.")
    if duration < MIN_DURATION:
        raise MediaError("At least 2 seconds of audio is required.")
    return samples


def window_ranges(length: int, sample_rate: int = SAMPLE_RATE):
    window = int(WINDOW_SECONDS * sample_rate)
    hop = int(HOP_SECONDS * sample_rate)
    if length <= window:
        yield 0, length
        return
    starts = list(range(0, length - window + 1, hop))
    if starts[-1] + window < length:
        starts.append(length - window)  # Full final window covers the tail.
    for start in starts:
        yield start, min(start + window, length)


def energy_quality(samples: np.ndarray, rate: int = SAMPLE_RATE) -> dict:
    frame = int(rate * 0.02)
    rms = [float(np.sqrt(np.mean(samples[i:i + frame] ** 2))) for i in range(0, len(samples), frame)]
    active_ratio = float(np.mean(np.array(rms) >= ENERGY_FLOOR)) if rms else 0.0
    return {"active_energy_ratio": round(active_ratio, 4),
            "clipped_sample_ratio": round(float(np.mean(np.abs(samples) >= 0.999)), 4),
            "rms": round(float(np.sqrt(np.mean(samples ** 2))), 5)}


def label(score):
    if score is None:
        return "inconclusive"
    return "synthetic" if score >= HIGH_THRESHOLD else "authentic" if score <= LOW_THRESHOLD else "inconclusive"


def aggregate_scores(segments: list, duration: float):
    """Average overlapping scores at each instant; integrate without double counting time."""
    valid = [s for s in segments if s["synthetic_score"] is not None]
    boundaries = sorted({v for s in valid for v in (s["start_seconds"], s["end_seconds"])})
    total = coverage = 0.0
    for left, right in zip(boundaries, boundaries[1:]):
        covering = [s["synthetic_score"] for s in valid
                    if s["start_seconds"] <= left and s["end_seconds"] >= right]
        if covering:
            total += (right - left) * float(np.mean(covering))
            coverage += right - left
    return (round(total / coverage, 4) if coverage else None,
            round(coverage / duration, 4) if duration else 0.0)


def suspicious_regions(segments):
    regions = []
    for s in segments:
        if s["synthetic_score"] is None or s["synthetic_score"] < HIGH_THRESHOLD:
            continue
        if regions and s["start_seconds"] <= regions[-1]["end_seconds"]:
            r = regions[-1]
            r["end_seconds"] = max(r["end_seconds"], s["end_seconds"])
            r["peak_score"] = max(r["peak_score"], s["synthetic_score"])
            r["segment_ids"].append(s["id"])
        else:
            regions.append({"start_seconds": s["start_seconds"], "end_seconds": s["end_seconds"],
                            "peak_score": s["synthetic_score"], "segment_ids": [s["id"]]})
    return regions


def analyze(samples: np.ndarray, detector, progress=lambda *args: None):
    ranges = list(window_ranges(len(samples)))
    segments = []
    for index, (start, end) in enumerate(ranges):
        clip = samples[start:end]
        quality = energy_quality(clip)
        prediction = {"synthetic_score": None, "evidence": []}
        if quality["active_energy_ratio"] >= 0.08:
            prediction = validate_prediction(detector.predict(clip, SAMPLE_RATE))
        else:
            prediction["evidence"] = ["Very little audible energy. This window was not scored by the detector."]
        segments.append({"id": index + 1, "start_seconds": round(start / SAMPLE_RATE, 5),
                         "end_seconds": round(end / SAMPLE_RATE, 5), **prediction,
                         "assessment": label(prediction["synthetic_score"]), "quality": quality})
        progress("detecting", 25 + round(60 * (index + 1) / len(ranges)))
    duration = len(samples) / SAMPLE_RATE
    score, coverage = aggregate_scores(segments, duration)
    quality = energy_quality(samples)
    warnings = ["Segment scores localize detector responses; they do not establish the cause of an artifact.",
                "Synthetic speech is not inherently a scam. Authentic speech may still contain scam content.",
                "Energy screening is not speech recognition. Speech presence must be verified separately."]
    if coverage < 0.5:
        warnings.append("Less than half of the timeline was scored; the overall assessment is inconclusive.")
    if quality["clipped_sample_ratio"] > 0.01:
        warnings.append("Audio clipping may affect detector reliability.")
    # Small waveform payload, computed from actual normalized audio, not random bars.
    waveform = [round(float(np.max(np.abs(chunk))), 4)
                for chunk in np.array_split(samples, min(240, len(samples)))]
    return {"duration_seconds": round(duration, 5), "sample_rate": SAMPLE_RATE, "channels": 1,
            "segments": segments, "synthetic_score": score, "scored_coverage": coverage,
            "assessment": label(score) if coverage >= 0.5 else "inconclusive",
            "suspicious_regions": suspicious_regions(segments), "quality": quality,
            "waveform": waveform, "warnings": warnings,
            "configuration": {"window_seconds": WINDOW_SECONDS, "hop_seconds": HOP_SECONDS,
                              "low_threshold": LOW_THRESHOLD, "high_threshold": HIGH_THRESHOLD,
                              "aggregation": "time-weighted mean of overlapping window scores",
                              "threshold_status": "provisional; calibrate on held-out development data",
                              "score_interpretation": "model score, not a calibrated probability"}}
