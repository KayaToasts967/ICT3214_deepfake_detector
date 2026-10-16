import io
import logging
import tempfile
import time
import unittest
import wave
from pathlib import Path
from unittest.mock import patch
import subprocess

import numpy as np
from fastapi.testclient import TestClient

from backend import main
from backend.detectors import DemoDetector, validate_prediction
from backend.pipeline import (SAMPLE_RATE, aggregate_scores, analyze, ffmpeg_executable,
                              suspicious_regions, window_ranges)

logging.disable(logging.CRITICAL)


def wav_bytes(seconds=8, silence=False, rate=16000):
    t = np.arange(int(seconds * rate)) / rate
    signal = np.zeros_like(t) if silence else .2 * np.sin(2 * np.pi * 220 * t)
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes((signal * 32767).astype("<i2").tobytes())
    return output.getvalue()


class PipelineTests(unittest.TestCase):
    def test_tail_is_fully_covered(self):
        windows = list(window_ranges(7 * SAMPLE_RATE))
        self.assertEqual(windows, [(0, 64000), (32000, 96000), (48000, 112000)])
        self.assertEqual(windows[-1][1], 7 * SAMPLE_RATE)

    def test_short_valid_recording_is_one_window(self):
        self.assertEqual(list(window_ranges(2 * SAMPLE_RATE)), [(0, 32000)])

    def test_overlap_aggregation_does_not_count_duration_twice(self):
        windows = [{"start_seconds": 0, "end_seconds": 4, "synthetic_score": 0},
                   {"start_seconds": 2, "end_seconds": 6, "synthetic_score": 1},
                   {"start_seconds": 4, "end_seconds": 8, "synthetic_score": 1}]
        score, coverage = aggregate_scores(windows, 8)
        self.assertEqual(score, .625)  # 2*0 + 2*.5 + 2*1 + 2*1, divided by 8
        self.assertEqual(coverage, 1)

    def test_unscored_windows_do_not_become_zero_scores(self):
        result = aggregate_scores([{"start_seconds": 0, "end_seconds": 4, "synthetic_score": None}], 4)
        self.assertEqual(result, (None, 0))

    def test_regions_merge_overlap_but_keep_disjoint_regions(self):
        segments = [{"id": i, "start_seconds": start, "end_seconds": end, "synthetic_score": score}
                    for i, start, end, score in [(1,0,4,.8),(2,2,6,.9),(3,6,10,.2),(4,8,12,.7)]]
        regions = suspicious_regions(segments)
        self.assertEqual([(r["start_seconds"],r["end_seconds"]) for r in regions], [(0,6),(8,12)])
        self.assertEqual(regions[0]["peak_score"], .9)

    def test_silence_is_inconclusive(self):
        result = analyze(np.zeros(4 * SAMPLE_RATE, dtype=np.float32), DemoDetector())
        self.assertEqual(result["assessment"], "inconclusive")
        self.assertIsNone(result["synthetic_score"])
        self.assertEqual(result["scored_coverage"], 0)

    def test_invalid_detector_predictions_fail(self):
        for value in [float("nan"), float("inf"), -1, 1.1, True]:
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                validate_prediction({"synthetic_score": value})

    def test_no_explanation_is_invented(self):
        class Detector:
            def predict(self, samples, rate):
                return {"synthetic_score": .8}
        result = analyze(np.ones(4 * SAMPLE_RATE, dtype=np.float32) * .1, Detector())
        self.assertEqual(result["segments"][0]["evidence"], [])


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_runtime = tempfile.TemporaryDirectory()
        cls.runtime_patch = patch.object(main, "RUNTIME", Path(cls.temp_runtime.name))
        cls.runtime_patch.start()
        cls.context = TestClient(main.app)
        cls.client = cls.context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.context.__exit__(None, None, None)
        cls.runtime_patch.stop()
        cls.temp_runtime.cleanup()

    def wait(self, job_id):
        for _ in range(400):
            data = self.client.get(f"/api/analyses/{job_id}").json()
            if data["status"] in {"completed", "failed"}:
                return data
            time.sleep(.025)
        self.fail("Analysis did not finish")

    def upload(self, content, filename="test.wav", mode="demo"):
        return self.client.post("/api/analyses", files={"file": (filename, content)}, data={"mode": mode})

    def test_audio_upload_report_playback_and_deletion(self):
        response = self.upload(wav_bytes(rate=44100))
        self.assertEqual(response.status_code, 202)
        job_id = response.json()["id"]
        job = self.wait(job_id)
        self.assertEqual(job["status"], "completed")
        report = job["result"]
        self.assertEqual(report["mode"], "demo")
        self.assertEqual(report["sample_rate"], 16000)
        self.assertEqual(report["channels"], 1)
        self.assertEqual(len(report["segments"]), 3)
        self.assertIn("DEMONSTRATION ONLY", report["warnings"][0])
        self.assertEqual(self.client.get(f"/api/analyses/{job_id}/audio").status_code, 200)
        self.assertEqual(self.client.get(f"/api/analyses/{job_id}/report").json()["id"], job_id)
        self.assertEqual(self.client.delete(f"/api/analyses/{job_id}").status_code, 204)
        self.assertFalse((main.RUNTIME / job_id).exists())
        self.assertEqual(self.client.get(f"/api/analyses/{job_id}").status_code, 404)

    def test_live_mode_never_falls_back_to_demo(self):
        with patch.object(main, "DETECTOR", None):
            self.assertEqual(self.upload(wav_bytes(), mode="live").status_code, 503)

    def test_unsupported_empty_and_oversized_inputs(self):
        self.assertEqual(self.upload(b"something", "x.exe").status_code, 415)
        self.assertEqual(self.upload(b"").status_code, 400)
        with patch.object(main, "MAX_UPLOAD", 100):
            self.assertEqual(self.upload(wav_bytes()).status_code, 413)

    def test_bad_mode(self):
        self.assertEqual(self.upload(wav_bytes(), mode="mystery").status_code, 422)

    def test_corrupt_media_fails_cleanly(self):
        job_id = self.upload(b"not audio").json()["id"]
        job = self.wait(job_id)
        self.assertEqual(job["status"], "failed")
        self.assertIn("Cannot decode", job["error"])
        self.assertFalse((main.RUNTIME / job_id).exists())

    def test_short_audio_fails_cleanly(self):
        job_id = self.upload(wav_bytes(.5)).json()["id"]
        self.assertIn("At least 2 seconds", self.wait(job_id)["error"])

    def test_over_duration_recording_is_rejected_not_truncated(self):
        with patch("backend.pipeline.MAX_DURATION", 3):
            job_id = self.upload(wav_bytes(4)).json()["id"]
            self.assertIn("exceeds", self.wait(job_id)["error"])

    def test_content_adapter_cannot_overwrite_detection_fields(self):
        result = main.validate_content({"mode": "demo", "synthetic_score": 0,
                                       "transcript": [],
                                       "scam_analysis": {"status": "completed", "risk": "low", "cues": []}}, 4)
        self.assertEqual(set(result), {"transcript", "scam_analysis"})

    def test_silent_upload_is_inconclusive(self):
        job_id = self.upload(wav_bytes(4, silence=True)).json()["id"]
        self.assertEqual(self.wait(job_id)["result"]["assessment"], "inconclusive")

    def test_video_and_mp3_decoding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.wav").write_bytes(wav_bytes(4))
            for filename, arguments in [("test.mp4", ["-f","lavfi","-i","color=c=blue:s=160x120:r=5", "-i", str(root / "source.wav"), "-c:v","libx264","-c:a","aac","-shortest"]),
                                        ("test.mp3", ["-i", str(root / "source.wav"), "-c:a","libmp3lame"])]:
                output = root / filename
                subprocess.run([ffmpeg_executable(),"-nostdin","-loglevel","error",*arguments,"-y",str(output)],check=True,
                               creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                job_id = self.upload(output.read_bytes(),filename).json()["id"]
                job = self.wait(job_id)
                self.assertEqual(job["status"], "completed")
                self.assertAlmostEqual(job["result"]["duration_seconds"], 4, delta=.2)

    def test_video_without_audio_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "silent.mp4"
            subprocess.run([ffmpeg_executable(),"-nostdin","-loglevel","error","-f","lavfi","-i",
                            "color=c=blue:s=160x120:r=5","-t","2","-an","-y",str(output)], check=True,
                           creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            job_id = self.upload(output.read_bytes(),"silent.mp4").json()["id"]
            self.assertIn("without audio", self.wait(job_id)["error"])

    def test_model_failure_does_not_report_authenticity(self):
        class Broken:
            def predict(self, samples, rate):
                raise RuntimeError("checkpoint error")
        with patch.object(main,"DETECTOR",Broken()):
            job_id = self.upload(wav_bytes(4),mode="live").json()["id"]
            job = self.wait(job_id)
            self.assertEqual(job["status"], "failed")
            self.assertIsNone(job["result"])

    def test_live_adapter_and_separate_content_result(self):
        class Detector:
            name, version = "Test detector", "test-1"
            def predict(self, samples, rate):
                assert rate == 16000 and samples.dtype == np.float32
                return {"synthetic_score": .8, "evidence": ["Test model evidence"]}
        class Content:
            def analyze(self, audio):
                return {"transcript": [{"start_seconds":0,"end_seconds":1,"text":"Test transcript"}],
                        "scam_analysis": {"status":"completed","risk":"low","cues":[]}}
        with patch.object(main,"DETECTOR",Detector()), patch.object(main,"CONTENT_ANALYZER",Content()):
            job_id = self.upload(wav_bytes(4),mode="live").json()["id"]
            report = self.wait(job_id)["result"]
            self.assertEqual(report["mode"], "live")
            self.assertEqual(report["assessment"], "synthetic")
            self.assertEqual(report["scam_analysis"]["risk"], "low")
            self.assertEqual(report["transcript"][0]["text"], "Test transcript")

    def test_content_failure_preserves_detector_report(self):
        class Content:
            def analyze(self, audio):
                raise RuntimeError("transcription failed")
        with patch.object(main,"DETECTOR",DemoDetector()), patch.object(main,"CONTENT_ANALYZER",Content()):
            job_id = self.upload(wav_bytes(4),mode="live").json()["id"]
            report = self.wait(job_id)["result"]
            self.assertEqual(report["scam_analysis"]["status"], "failed")
            self.assertIsNotNone(report["synthetic_score"])

    def test_expired_results_delete_audio(self):
        job_id = self.upload(wav_bytes(4)).json()["id"]
        self.wait(job_id)
        with main.LOCK:
            main.JOBS[job_id]["updated_at"] = time.time() - 1900
        self.assertEqual(self.client.get(f"/api/analyses/{job_id}").status_code, 404)
        self.assertFalse((main.RUNTIME / job_id).exists())


if __name__ == "__main__":
    unittest.main()
