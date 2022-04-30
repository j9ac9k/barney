from __future__ import annotations

import logging
from random import random
from time import time
from typing import TYPE_CHECKING

import numpy as np
import pytest  # noqa: F401

from ..helpers import openFile, rowSelector
from ..markers import skip_if_no_audio_output_device, skip_if_skip_flag

if TYPE_CHECKING:
    from pytestqt import qtbot
    from qtpy.QtCore import QUrl

    from barney.views.MainWindow import MainWindow


logger = logging.getLogger(__name__)


@skip_if_skip_flag
@skip_if_no_audio_output_device
def test_play_and_stop(viewer: MainWindow, wavPath: QUrl, qtbot: qtbot):
    openFile(viewer, wavPath, qtbot)
    rowSelector(viewer, 0, qtbot)
    playbackController = viewer._controller.playbackController

    logger.debug("Playing Global Region")
    with qtbot.waitSignal(playbackController.sigPlaybackStarted, timeout=500):
        viewer.playGlobalRegion()
    # assert playbackController.runningStream.active

    logger.debug("Stopping Playback")
    with qtbot.waitSignal(playbackController.sigPlaybackStopped, timeout=1500):
        viewer.sigStopRequested.emit()


@skip_if_skip_flag
@skip_if_no_audio_output_device
def test_play_spam(viewer: MainWindow, wavPath: QUrl, qtbot: qtbot):
    openFile(viewer, wavPath, qtbot)
    rowSelector(viewer, 0, qtbot)

    pclogger = logging.getLogger("barney.controllers.PlaybackController")
    logger.debug("Disabling PlaybackController logger for spam play loop")
    pclogger.disabled = True
    for _ in range(10):
        viewer.playGlobalRegion()
    logger.debug("Re-enabling PlaybackController logger")
    pclogger.disabled = False


class PosCatcher:
    def __init__(self):
        self.callback1 = -1.0

    def catchPos(self, pos: int):
        if self.callback1 < 0:
            self.callback1 = time()

    def convertToTimeElapsed(self, t: float):
        self.callback1 -= t

    def convertToMs(self):
        self.callback1 *= 1000


@skip_if_skip_flag
@skip_if_no_audio_output_device
def test_latency(viewer: MainWindow, wavPath: QUrl, qtbot: qtbot):
    openFile(viewer, wavPath, qtbot)
    rowSelector(viewer, 0, qtbot)
    playbackController = viewer._controller.playbackController

    catcher = PosCatcher()
    playbackController.sigPlaybackPosition.connect(catcher.catchPos)

    t = time()
    viewer.playGlobalRegion()
    # for _ in range(2):
    #     with qtbot.waitSignal(playbackController.sigPlaybackPosition, timeout=200):
    #         assert playbackController.runningStream.active

    catcher.convertToTimeElapsed(t)
    catcher.convertToMs()

    logger.info(f"Latency test result {catcher.callback1:.2f} ms.")

    threshold = 128
    assert catcher.callback1 < threshold, (
        f"time til first callback:\t{catcher.callback1:.4f} ms, "
        + f"threshold: {threshold} ms"
    )


@skip_if_skip_flag
@skip_if_no_audio_output_device
def test_callback(viewer: MainWindow, wavPath: QUrl, qtbot: qtbot):
    import sounddevice as sd

    openFile(viewer, wavPath, qtbot)
    rowSelector(viewer, 0, qtbot)
    pc = viewer._controller.playbackController
    wave = pc.wave

    if not hasattr(pc.callback, "index"):
        pc.callback.index, pc.callback.stopIndex = viewer.plotView.region.getRegion()
        pc.callback.index = int(pc.callback.index)
        pc.callback.stopIndex = int(pc.callback.stopIndex)

    assert 0 <= pc.callback.index < pc.callback.stopIndex <= len(wave._value)
    i = pc.callback.index
    stop_index = pc.callback.stopIndex

    while i <= stop_index:
        samples = int(random() * 2**6) + 65
        end_position = samples + i
        outdata = np.empty((samples, wave.value.shape[1]), dtype=wave.dtype)

        try:
            pc.callback(outdata, (samples), None, None)
        except sd.CallbackStop:
            logger.debug("Callback Stop Called")
            assert end_position >= stop_index

        if end_position < stop_index:
            assert all(outdata == wave._value[i:end_position, :])
        else:
            assert all(outdata[: stop_index - i, :] == wave._value[i:stop_index, :])
            assert all(outdata[stop_index - i :, :] == 0)
        i = end_position
