from __future__ import annotations

import dataclasses
import logging
from math import ceil, log10  # faster than np.log10 for single values
from typing import TYPE_CHECKING

import numpy as np
from pyqtgraph import ColorMap
from qtpy.QtCore import QThread, Signal, Slot
from scipy.signal import windows
from signalworks.dsp import frame_centered

from barney.Utilities.colorMaps import c_maps as mpl_cmaps
from barney.Utilities.ConfigClass import ConfigClass

from .SubPlotController import SubPlotController

if TYPE_CHECKING:
    from typing import Callable, Dict, Optional, Tuple

    from qtpy.QtCore import QMetaObject, QObject
    from signalworks import Wave

    from ..PlotController import PlotController
    from .WaveformController import AGGR_FUNC_TYPE

logger = logging.getLogger(__name__)


class SpectrogramCalculationThread(QThread):

    sigSpectrogramComputed = Signal(object)
    sigFrameComputed = Signal(object)

    def __init__(
        self,
        parent: Optional[QObject],
        wave: Wave,
        windowDuration: float,
        spectrogramTime: np.ndarray,
        window: Callable[[int], np.ndarray],
        NFFT: int,
        normalize_signal: bool,
        normalize_output: bool,
        pre_emphasis: Optional[float],
        channel_aggregate: AGGR_FUNC_TYPE,
    ):
        super().__init__(parent)
        self.wave = wave
        self.windowDuration = windowDuration
        self.spectrogramTime = spectrogramTime
        self.window = window
        self.NFFT = NFFT
        self.normalize_signal = normalize_signal
        self.normalize_output = normalize_output
        self.pre_emphasis = pre_emphasis
        self.channel_aggregate = channel_aggregate

    def run(self) -> None:
        if self.normalize_signal:
            s = self.wave.value / np.abs(np.max(self.wav.value))
        else:
            s = self.wave.value.astype(np.float64)

        if self.wave.value.shape[1] > 1:
            s = self.channel_aggregate(s, axis=1)  # type: ignore

        ftr = frame_centered(
            s.flatten(),
            self.spectrogramTime,
            int(round(self.windowDuration * self.wave.fs)),
        )
        ftr *= self.window(ftr.shape[1])
        self.sigFrameComputed.emit(ftr.copy())

        if self.pre_emphasis is not None:
            ftr[:, 1:-1] -= self.pre_emphasis * np.roll(ftr, -1, axis=1)[:, 1:-1]
        M = np.absolute(np.fft.rfft(ftr, n=self.NFFT))
        np.clip(M, np.finfo(M.dtype).eps, None, out=M)
        M[:] = 1 + np.log10(M) * 20
        frequency = np.arange(M.shape[1]) / M.shape[1] * self.wave.fs / 2
        self.sigSpectrogramComputed.emit((M, frequency))


@dataclasses.dataclass
class SpectrogramControllerSettings(ConfigClass):
    _preEmphasis: float = 0.97
    _freqCutoff: int = 8_000
    _enableFreqCutoff: bool = False
    _enablePreEmphasis: bool = True
    _highCap: int = 100
    _lowCap: int = 0
    _window: str = "hann"
    _windowDuration: float = 0.01
    _colorMap: str = "viridis"
    _invertColors: bool = False
    spectrogramLineColor: Tuple[int, int, int, int] = (255, 160, 0, 255)
    specHigh: float = 100.0
    specLow: float = 0.0

    def __init__(self, config_key: str = ""):
        super().__init__(config_key)


class SpectrogramController(SubPlotController):
    sigApplyColorMap = Signal(np.ndarray)

    def __init__(self, parent: PlotController) -> None:
        self._initColorMapsDict()  # must exist before other defaults are set
        super().__init__(parent)
        self.settings = SpectrogramControllerSettings(config_key="Spectrogram Options")
        self.queuedThread: Optional[SpectrogramCalculationThread] = None
        self.currentThread: Optional[SpectrogramCalculationThread] = None
        self.startTime = 0
        self.metaObjects: Optional[Tuple[QMetaObject, QMetaObject]] = None

    @Slot()
    def threadFinished(self) -> None:
        self.currentThread = None
        self.startNextThread()

    def startNextThread(self) -> None:
        if self.currentThread is None and isinstance(
            self.queuedThread, SpectrogramCalculationThread
        ):
            self.currentThread, self.queuedThread = self.queuedThread, None
            self.currentThread.start()
        return None

    def _initColorMapsDict(self) -> None:
        # colorsmaps!
        self.colorMaps: Dict[str, np.ndarray] = {}
        # grab the matplotlib colors
        for color_name, values in mpl_cmaps.items():
            colorMap = ColorMap(
                np.linspace(0.0, 1.0, len(values), endpoint=True),
                np.rint(255 * np.array(values)).clip(0, 255).astype(np.ubyte),
            )
            self.colorMaps[color_name] = colorMap.getLookupTable(alpha=True)
        # insert the gray color scheme
        gray_color = np.array([(0, 0, 0), (255, 255, 255)], dtype=np.ubyte)
        gray_cmap = ColorMap(np.array([0.0, 1.0]), gray_color)
        self.colorMaps["grayscale"] = gray_cmap.getLookupTable(alpha=True)

    def refreshSubPlot(self) -> None:
        self.plotView.spectrogram.updateSpectrogram()
        logger.debug("Spectrogram refreshed")

    def newSpectrogramArray(self, screen_height: int) -> None:
        screenGeometryNFFT = screen_height * 2  # FFT is mirrored across 0
        if self.enableFreqCutoff:
            # in case the cutoff is above nyquist...
            if self.freqCutoff > self.wave.fs // 2:
                logger.warning(
                    f"Cutoff frequency {self.freqCutoff} > nyquist frequency {self.wave.fs // 2}, setting cutoff to {self.wave.fs // 2}"
                )
            cutoffFreq = min(self.wave.fs // 2, self.freqCutoff)
            screenGeometryNFFT *= self.wave.fs / (2 * cutoffFreq)
        NFFT = 2 ** ceil(screenGeometryNFFT).bit_length()

        wcontroller = self.plotController.waveController
        channel_aggregate = wcontroller.poolFuncMap[
            wcontroller.settings.audioChannelPooling
        ]

        spectrogramCalcThread = SpectrogramCalculationThread(
            parent=None,
            wave=self.wave,
            windowDuration=self.windowDuration,
            spectrogramTime=self.plotView.spectrogram.spectrogramTime,
            window=getattr(windows, self.window),
            NFFT=NFFT,
            normalize_signal=False,
            normalize_output=False,
            pre_emphasis=self.preEmphasis if self.enablePreEmphasis else None,
            channel_aggregate=channel_aggregate,
        )

        metaSpectrogramComputed = spectrogramCalcThread.sigSpectrogramComputed.connect(
            self.plotView.spectrogram.newSpectrogramImage
        )
        metaSpectrogramCalcThread = spectrogramCalcThread.sigFrameComputed.connect(
            self.plotView.logEnergyPlot.updateEnergyPlot
        )

        self.metaObjects = (metaSpectrogramComputed, metaSpectrogramCalcThread)
        spectrogramCalcThread.finished.connect(self.threadFinished)
        self.queuedThread = spectrogramCalcThread
        self.startNextThread()

    def calculateSpectrogramLimits(self) -> None:
        """Method calculates what the color limits should be on a per-file basis"""
        if self.wave is None:
            return None

        frame_width = int(self.wave.fs * 0.05)
        NFFT = 2 ** frame_width.bit_length()

        n_frames = 1 + self.wave.duration // frame_width

        # get non-overlapping 50 ms frames of the entire signal
        frames = np.resize(self.wave.value, (frame_width, n_frames))

        # TODO: faster with np.einsum?
        energy = (frames**2).sum(axis=0)
        spec = np.abs(np.fft.rfft(frames[:, energy.argmax()], NFFT))
        # using log10 instead of np.log10 because its faster w/ single values
        # adding epsilon to deal with the case of audio files of all zeros
        self.settings.specHigh = 20 * log10(spec.max() + np.finfo(spec.dtype).eps)
        self.settings.specLow = 0.0

    def clippedSpectrogram(
        self, original: np.ndarray, low: int, high: int
    ) -> np.ndarray:
        X = original.copy()

        range_ = self.settings.specHigh - self.settings.specLow
        min_ = self.settings.specLow + range_ * (low / 100)
        max_ = self.settings.specHigh - range_ * ((100 - high) / 100)
        X = np.clip(X, min_, max_)
        return X

    @property
    def preEmphasis(self) -> float:
        return self.settings._preEmphasis

    @preEmphasis.setter
    def preEmphasis(self, value: float) -> None:
        if self.settings._preEmphasis != value:
            self.settings._preEmphasis = value
            if self.settings._enablePreEmphasis:
                self.plotView.spectrogram.updateSpectrogram()

    @property
    def freqCutoff(self) -> int:
        return self.settings._freqCutoff

    @freqCutoff.setter
    def freqCutoff(self, value: int) -> None:
        if self.settings._freqCutoff != value:
            self.settings._freqCutoff = value
            if self.settings._enableFreqCutoff:
                self.plotView.spectrogram.updateSpectrogram()

    @property
    def enableFreqCutoff(self) -> bool:
        return self.settings._enableFreqCutoff

    @enableFreqCutoff.setter
    def enableFreqCutoff(self, enable: bool) -> None:
        if self.settings._enableFreqCutoff != enable:
            self.settings._enableFreqCutoff = enable
            self.plotView.spectrogram.updateSpectrogram()

    @property
    def enablePreEmphasis(self) -> bool:
        return self.settings._enablePreEmphasis

    @enablePreEmphasis.setter
    def enablePreEmphasis(self, enable: bool) -> None:
        if self.settings._enablePreEmphasis != enable:
            self.settings._enablePreEmphasis = enable
            self.plotView.spectrogram.updateSpectrogram()

    @property
    def lowCap(self) -> int:
        return self.settings._lowCap

    @lowCap.setter
    def lowCap(self, value: int) -> None:
        if self.settings._lowCap != value:
            self.settings._lowCap = value
            self.applyClip()

    @property
    def highCap(self) -> int:
        return self.settings._highCap

    @highCap.setter
    def highCap(self, value: int) -> None:
        if self.settings._highCap != value:
            self.settings._highCap = value
            self.applyClip()

    def applyClip(self) -> None:
        self.plotView.spectrogram.clipSpectrogram(self.lowCap, self.highCap)

    @property
    def windowDuration(self) -> float:
        """Getter for the Window Duration Property

        Returns
        -------
        float
            The duration (in seconds) for each window
        """
        return self.settings._windowDuration

    @windowDuration.setter
    def windowDuration(self, value: float) -> None:
        if self.settings._windowDuration != value:
            self.settings._windowDuration = value
            self.plotView.spectrogram.updateSpectrogram()

    @property
    def window(self) -> str:
        return self.settings._window

    @window.setter
    def window(self, window: str) -> None:
        """Window Property Setter

        Parameters
        ----------
        window : Union[Callable[[int], np.ndarray], str]
            Either name of window (where it is listed in scipy.signal.windows) or
            provide your own window function that takes in an integer and returns
            a numpy array of the corresponding scalars of the window
        """
        if window == "hanning":
            window = "hann"
        if not hasattr(windows, window):
            raise KeyError(f"{window} not a valid option for windowing.")
        self.settings._window = window

    @property
    def colorMap(self) -> str:
        return self.settings._colorMap

    @colorMap.setter
    def colorMap(self, name: str) -> None:
        if name not in self.colorMaps:
            logger.error(
                f"Color Map {name} is not among the list of available colormaps: {', '.join(list(self.colorMaps.keys()))}"
            )
            return None
        self.settings._colorMap = name
        self.applyColorMap()

    @property
    def invertColors(self) -> bool:
        return self.settings._invertColors

    @invertColors.setter
    def invertColors(self, invert: bool) -> None:
        self.settings._invertColors = invert
        self.applyColorMap()

    def applyColorMap(self) -> None:
        lut = self.colorMaps[self.colorMap]
        if self.invertColors:
            lut = np.flipud(lut)
        self.sigApplyColorMap.emit(lut)

    def applySpectrogramLineColor(self, color: Tuple[int, int, int, int]) -> None:
        self.settings.spectrogramLineColor = color
        self.plotView.spectrogram.verticalLine.setPen(color)
        self.plotView.spectrogram.horizontalLine.setPen(color)
