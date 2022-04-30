from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from qtpy.QtCore import QObject, Signal
from signalworks.tracking import Wave

from .SubPlotControllers.FontController import FontController
from .SubPlotControllers.SpectrogramController import SpectrogramController
from .SubPlotControllers.WaveformController import WaveformController

# from .SubPlotControllers.LogEnergyController import LogEnergyController

if TYPE_CHECKING:
    from typing import Any, Optional, Union

    from ..views.PlotArea import PlotView
    from .controller import MainController

logger = logging.getLogger(__name__)


class PlotController(QObject):
    showWaveform = Signal()
    fileNotFound = Signal()
    updateNotificationInterval = Signal(float)
    sigSetPlaybackPosition = Signal(int)

    def __init__(self, parent: MainController) -> None:
        super().__init__(parent)
        self.mainController = parent
        self.plotView: PlotView

        self.specController = SpectrogramController(self)
        self.waveController = WaveformController(self)
        self.fontController = FontController(self)
        # self.logEnergyController = LogEnergyController(self)

        # track properties
        self._waveAverage: Optional[float] = None
        self._waveMaxAmplitude: Optional[Union[float, int]] = None
        self._waveDuration: Optional[int] = None
        self._waveSamples: Optional[int] = None
        self._connect()

    def _connect(self) -> None:
        self.parent().sigPlaybackPosition.connect(self.sigSetPlaybackPosition)

    def _needs_update(self, attribute: str, value: Any) -> bool:
        return hasattr(self, attribute) and value != getattr(self, attribute)

    @property
    def wave(self) -> Optional[Wave]:
        return self.mainController._model.currentWaveform

    @wave.setter
    def wave(self, track: Wave) -> None:
        self.mainController._model.currentWaveform = track
        self._waveAverage = np.mean(track._value)
        self._waveMaxAmplitude = track._value[
            np.unravel_index(np.argmax(track._value, axis=None), track._value.shape)
        ]
        self._waveDuration = int((track._value.shape[0] / track.fs) * 1_000)
        self._waveSamples = track._value.shape[0]

    def receiveTrack(self, track: Wave) -> None:
        logger.debug("Receive Track Called")
        self.wave = track

        # run this so specotrgram color no longer shifts as spectrogram moves around
        self.specController.calculateSpectrogramLimits()
        self.showWaveform.emit()
        self.waveController.determineClippedRegions()

    def receiveNothing(self) -> None:
        self.fileNotFound.emit()
