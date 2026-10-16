"""Copy this into your member's module and implement predict. Never enable as-is."""


class TeamDetector:
    name = "WavLM robust detector"
    version = "replace-with-checkpoint-version"

    def __init__(self):
        # Load your trained model, checkpoint, and feature processor ONCE here.
        # Set model.eval(); use torch.inference_mode() inside predict.
        raise NotImplementedError("Member 1 must supply the trained detector and checkpoint.")

    def predict(self, samples, sample_rate):
        # samples: contiguous mono float32 numpy array, amplitude [-1, 1], 16 kHz.
        # Duration: 2–4 seconds; pad only if your training setup requires it.
        # Return the score for the SYNTHETIC class, never the real class.
        # Apply your training feature normalization here. The API only resamples.
        # Optional evidence must come from the model's actual explanation method.
        raise NotImplementedError


def create_detector():
    return TeamDetector()
