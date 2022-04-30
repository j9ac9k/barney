from __future__ import annotations

import logging
from contextlib import suppress
from time import time
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd
from qtpy.QtCore import QObject, Signal, Slot
from typing_extensions import (  # Protocol may be moved to typing in future versions
    Protocol,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from types import TracebackType
    from typing import Any, Optional, Type

    from signalworks.tracking import Wave

    from .controller import MainController


class CallbackProtocol(Protocol):
    sigPlaybackPosition: Signal
    index: int
    stopIndex: int
    data: np.ndarray


def def_callback_decorator(callback_func: Any) -> CallbackProtocol:
    return callback_func


class PlaybackController(QObject):
    sigPlaybackPosition = Signal(int)
    sigPlaybackStopped = Signal()
    sigPlaybackStarted = Signal()

    def __init__(self, parent: MainController) -> None:
        super().__init__(parent)
        parent.sigStopRequested.connect(self.stopPlaybackRequested)
        parent.sigPlayRequested.connect(self.startPlayback)
        # suppress this error as we don't actually need a working audio device to run Barney on startup
        with suppress(sd.PortAudioError):
            self.currentDevice = sd.query_devices(kind="output")

        self.sigPlaybackPosition.connect(parent.sigPlaybackPosition)
        self.callback.sigPlaybackPosition = self.sigPlaybackPosition

        self.last_play = time()
        self.stream: sd.OutputStream = None
        self.runningStream: sd.OutputStream = None
        self._blockSize = 512
        self.index: int
        self.stopIndex: int
        self.playbackMechanism = "standard"

        self.extraLogs = 0
        if self.extraLogs:
            ExtraSounddeviceLogging.sounddeviceDump(self)

    @property
    def wave(self) -> Optional[Wave]:
        return self.parent()._model.currentWaveform

    @property
    def blockSize(self) -> int:
        return self._blockSize

    @blockSize.setter
    def blockSize(self, value: int) -> None:
        self.blockSize = int(np.clip(value, 64, 4096))

    def simplePlay(self) -> None:
        """Method can be used instead of the more complex runningStream.start()"""
        if self.wave is None:
            return None

        trackChannels = self.wave._value.shape[1]
        channels = (
            1
            if trackChannels > PlaybackController.supportedChannels()
            else trackChannels
        )

        audioData = self.wave._value[self.index : self.stopIndex, :].copy()
        if channels == 1:
            audioData = audioData.mean(axis=1)
            audioData = audioData.reshape(-1, 1)

        sd.play(
            audioData,
            samplerate=self.wave._fs,
            blocksize=self._blockSize,
            latency="high",
        )

    @Slot()
    def stopPlaybackRequested(self) -> None:
        """Slot called when the user wants to stop audio playback"""
        if self.runningStream is not None and self.runningStream.active:
            self.runningStream.stop()
            logger.debug("Running Stream stop command returned")
            return None
        else:
            # using simplePlay
            sd.stop()

    def stopPlaybackCompleted(self) -> None:
        """Method called when the running stream has stopped"""
        self.runningStream = None
        self.sigPlaybackPosition.emit(0)
        self.sigPlaybackStopped.emit()

    @Slot(int, int)
    def startPlayback(self, start: int, finish: int) -> None:
        logger.debug("Start Playback Slot Called ")
        if self.wave is None:
            return None

        t = time()
        under_threshold = t - self.last_play < 0.1
        self.last_play = t

        if under_threshold:
            logger.warning("Time since last play event under threshold.")
            return
        if self.runningStream is not None:
            self.stopPlaybackRequested()

        if self.stream is None:
            logger.warning("stream was not prepped prior to Playback")
            self.prepAudioStream()

        self.callback.index = self.index = start
        self.callback.stopIndex = self.stopIndex = finish
        self.runningStream = self.stream
        logger.debug(f"Starting audio on {sd.query_devices(kind='output')}")
        with ExtraSounddeviceLogging(self):
            if self.playbackMechanism == "standard":
                self.runningStream.start()
                self.prepAudioStream()
            else:
                self.simplePlay()
            self.sigPlaybackStarted.emit()

    @staticmethod
    @def_callback_decorator
    def callback(
        outdata: np.ndarray,
        frames: int,
        time: Optional[sd._ffi.Cdata],
        status: Optional[sd.CallbackFlags],
    ) -> None:
        self = PlaybackController.callback
        self.sigPlaybackPosition.emit(self.index)
        end_position = self.index + frames

        if end_position < self.stopIndex:
            outdata[:] = self.data[self.index : end_position, :]
        else:
            outdata[:] = np.vstack(
                (
                    self.data[self.index : self.stopIndex, :],
                    np.zeros(
                        (end_position - self.stopIndex, outdata.shape[1]),
                        dtype=outdata.dtype,
                    ),
                )
            )
            raise sd.CallbackStop

        self.index = end_position
        if status:
            logger.warning(f"sounddevice status: {status}")

    def prepAudioStream(self) -> None:
        if self.wave is None:
            return
        if self.extraLogs:
            ExtraSounddeviceLogging.sounddeviceDump(self)

        trackChannels = self.wave._value.shape[1]
        channels = (
            1
            if trackChannels > PlaybackController.supportedChannels()
            else trackChannels
        )

        if channels == 1:
            audioData = self.wave._value.mean(axis=1)
            self.callback.data = audioData.reshape(-1, 1)
        else:
            self.callback.data = self.wave._value

        with ExtraSounddeviceLogging(self):
            self.stream = sd.OutputStream(
                samplerate=self.wave._fs,
                blocksize=self._blockSize,
                dtype=self.wave._value.dtype
                if self.wave._value.dtype != np.float64
                else np.float32,
                channels=channels,
                callback=self.callback,
                finished_callback=self.stopPlaybackCompleted,
                prime_output_buffers_using_stream_callback=False,
                latency="high",
            )

    @staticmethod
    def supportedChannels() -> int:
        return sd.query_devices(device=sd.default.device[1], kind="output")[
            "max_output_channels"
        ]

    @Slot(str)
    def setAudioDevice(self, name: str) -> None:
        logger.info(f"Attempting to set output device to {name}")
        sd.default.device = None, name
        logger.debug(f"Default Output Device: {sd.query_devices(kind='output')}")

    @Slot(int)
    def setBufferSize(self, size: int) -> None:
        logger.info(f"Setting audio buffer size to {size}")
        self.blockSize = size


class ExtraSounddeviceLogging:
    """A context manager that will dump as much sounddevice info as it can
    when an exception occurs in its context."""

    def __init__(self, runner: PlaybackController = None) -> None:
        self.runner = runner

    def __enter__(self) -> None:
        pass

    def __exit__(self, etype: Type, value: BaseException, _: TracebackType) -> None:
        if value is not None:
            logger.debug(
                f"{etype.__name__} caught in {type(self).__name__} context manager"
            )
            ExtraSounddeviceLogging.sounddeviceDump(self.runner)

    @staticmethod
    def sounddeviceDump(playbackController: PlaybackController = None) -> None:
        logger.info("*** sounddevice info dump: ***")
        try:
            logger.info(f"default channels (in,out): {sd.default.channels}")
            logger.info(f"default device: {sd.default.device}")
            logger.info(f"available devices:\n{sd.query_devices()}")
            logger.info(f"portaudio version:\n{sd.get_portaudio_version()}")
            hostapis = "\n".join(map(str, sd.query_hostapis()))
            logger.info(f"host apis:\n{hostapis}")

            logger.info("** all defaults: **")
            for attr in [attr for attr in dir(sd.default) if not attr.endswith("__")]:
                logger.info(f"sd.default.{attr}:  {getattr(sd.default, attr)}")

        except BaseException as e:
            logger.error(
                f"{type(e).__name__} caught in PlaybackController.souddeviceDump"
            )
            logger.error(e)

        try:
            logger.warning("checking output settings")
            sd.check_output_settings()
            logger.info("check complete.")
            nchannels = PlaybackController.supportedChannels()
            logger.warning(f"checking output settings w/ channels={nchannels}")
            sd.check_output_settings(channels=nchannels)
            logger.info("check complete.")
        except BaseException as e:
            logger.error("check failed.")
            logger.error(f"{type(e).__name__} caught")
            logger.error(e)
