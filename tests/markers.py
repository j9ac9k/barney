import os

import pytest


def has_audio_device() -> bool:
    try:
        import sounddevice as sd

        device = sd.query_devices(kind="output")
        os.environ["ALSA_CARD"] = device["name"]
    except sd.PortAudioError:
        os.environ["ALSA_CARD"] = "default"
        return False
    else:
        return bool(device)


skip_if_no_audio_output_device = pytest.mark.skipif(
    not has_audio_device(), reason="No audio output device on found system."
)

skip_if_skip_flag = pytest.mark.skipif(
    os.getenv("SKIP_AUDIO_TEST") is not None,
    reason="Environment flag set to skip tests",
)
