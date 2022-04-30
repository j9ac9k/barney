from __future__ import annotations

import dataclasses
import logging
import operator
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QObject, QRectF, Slot
from qtpy.QtGui import QPainter, QPicture

from barney.Utilities.ConfigClass import ConfigClass

from .SubPlotController import SubPlotController

if TYPE_CHECKING:
    from typing import Any, Callable, Dict, List, Optional, Tuple

    from qtpy.QtWidgets import QStyleOptionGraphicsItem, QWidget
    from signalworks import Wave

    from ..PlotController import PlotController

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    AGGR_FUNC_TYPE = Callable[[np.ndarray, Any], np.ndarray]


class ClippedRegions(pg.GraphicsObject):
    def __init__(
        self,
        rects: List[QRectF],
        color: Tuple[int, int, int, int],
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._rects = rects
        self.color = color
        self.picture = QPicture()
        self._generatePicture()

    @property
    def rects(self) -> List[QRectF]:
        return self._rects

    def _generatePicture(self) -> None:
        painter = QPainter(self.picture)
        painter.setCompositionMode(QPainter.RasterOp_SourceOrDestination)
        painter.setPen(pg.functions.mkPen(self.color, width=0))
        painter.setBrush(pg.functions.mkBrush(self.color))
        for rect in self.rects:
            painter.drawRect(rect)
        painter.end()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: Optional[QWidget] = None,
    ) -> None:
        self.picture.play(painter)

    def boundingRect(self) -> QRectF:
        return QRectF(self.picture.boundingRect())

    def setBrush(self, color: Tuple[int, int, int, int]) -> None:
        self.color = color
        self._generatePicture()


@dataclasses.dataclass
class WaveformControllerSettings(ConfigClass):
    audioChannelPooling: str = "mean"
    clippingThreshold: float = 0.98
    clippingColor: Tuple[int, int, int, int] = (239, 83, 80, 127)
    clippingPaddingDuration = 1  # ms
    clipHighlighting = True

    def __init__(self, config_key: str):
        super().__init__(config_key)


class WaveformController(SubPlotController):
    poolFuncMap: Dict[str, AGGR_FUNC_TYPE] = {
        "mean": np.mean,
        # just slices, *args and **kwargs will be ignored
        "left": lambda a, *args, **kwargs: a[:, 0],
        "right": lambda a, *args, **kwargs: a[:, 1],
    }

    def __init__(self, parent: PlotController) -> None:
        super().__init__(parent)
        self.settings = WaveformControllerSettings(config_key="Waveform Options")
        self.clippedRects: List[QRectF] = []
        self.globalClippedRegions: Optional[ClippedRegions] = None
        self.localClippedRegions: Optional[ClippedRegions] = None
        self.clippedIndexes: np.ndarray = np.ndarray([])
        self.plottableWaveform: Optional[Tuple[np.ndarray, np.ndarray]] = None

    def calcPlottableWaveform(
        self, wave: Wave, axis: int = 1
    ) -> Tuple[np.ndarray, np.ndarray]:
        if wave._value.ndim == 1:
            self.plottableWaveform = (wave.time, wave._value)
        elif wave._value.ndim == 2:
            pool = WaveformController.poolFuncMap[self.settings.audioChannelPooling]
            self.plottableWaveform = wave.time, pool(wave._value, axis=axis)  # type: ignore
        else:
            raise ValueError(
                f"Invalid dimensions for input data array: {wave._value.ndim}."
            )
        return self.plottableWaveform

    @property
    def localViewBox(self) -> pg.ViewBox:
        return self.plotView.zoomPlot.vb

    @property
    def globalViewBox(self) -> pg.ViewBox:
        return self.plotView.mainPlot.vb

    @Slot(bool)
    def toggleClippingRegions(self, checked: bool) -> None:
        self.settings.clipHighlighting = checked
        if not checked:
            if self.localClippedRegions is not None:
                self.localViewBox.removeItem(self.localClippedRegions)
                # self.localClippedRegions = None
            if self.globalClippedRegions is not None:
                self.globalViewBox.removeItem(self.globalClippedRegions)
                # self.globalClippedRegions = None
            self.clippedRects.clear()
        else:
            self.updateClippedRegions()

    def resetToBarneyDefaults(self) -> None:
        super().resetToBarneyDefaults()

    def refreshSubPlot(self) -> None:
        logger.info(f"{type(self).__name__} refreshing waveform plot.")
        self.plotView.plotWaveform()

    def changeDualChannelPoolType(self, newpool: str) -> None:
        if newpool not in self.poolFuncMap:
            raise KeyError(
                f"{newpool} not a valid option for pooling multi-channel audio."
            )
        self.settings.audioChannelPooling = newpool
        logger.info(f"New multi-channel audio pooling method: {newpool}")
        self.refreshSubPlot()

    def toolTipText(self, sample: int) -> str:
        time_value = sample / self.wave.fs
        amplitude = self.wave.value[sample].mean()
        duration = int(
            np.rint(
                1000
                * abs(operator.sub(*self.plotView.region.getRegion()) / self.wave.fs)
            )
        )
        return (
            f"{'Time:':>10} {int(time_value * 1_000):,} ms\n"
            + f"{'Sample:':>10} {sample:,}\n"
            + f"{'Amplitude:':>10} {amplitude:,}\n"
            + f"{'Duration:':>10} {duration:,}"
        )

    def waveformInfoText(self) -> str:
        waveAverage = self.parent()._waveAverage
        waveMaxAmplitude = self.parent()._waveMaxAmplitude
        if isinstance(waveMaxAmplitude, np.integer):
            waveMaxAmplitudeString = f"{waveMaxAmplitude:,}"
        else:
            waveMaxAmplitudeString = f"{waveMaxAmplitude:.3f}"
        waveDuration = self.parent()._waveDuration
        waveSamples = self.parent()._waveSamples
        return (
            f"{'Mean Value':>12} {waveAverage:.4f}\n"
            + f"{'Max Value':>12} {waveMaxAmplitudeString}\n"
            + f"{'Duration':>12} {waveDuration:,} ms\n"
            + f"{'Samples':>12} {waveSamples:,}\n"
            + f"{'Sample Rate':>12} {self.wave.fs:,}"
        )

    @Slot(object)
    def updateClippingRegionColor(self, color: Tuple[int, int, int, int]) -> None:
        """Slot that receives the new color to set the shaded region to

        Args:
            color (Tuple[int, int, int, int]): (Red, Green, Blue, Alpha), all integers should be 0-255
        """
        self.settings.clippingColor = color
        if self.globalClippedRegions is not None:
            self.globalClippedRegions.setBrush(color)
        if self.localClippedRegions is not None:
            self.localClippedRegions.setBrush(color)

    @Slot(int)
    def determineClippedIndexes(self, percentage: Optional[int] = None) -> None:
        logger.debug(f"Received clip percentarge of {percentage}")
        if percentage is not None:
            self.settings.clippingThreshold = percentage / 100
        if self.wave is None:
            return None
        self.clippedIndexes = np.nonzero(
            np.abs(self.wave.value.T).max(axis=0)
            > self.settings.clippingThreshold * self.wave.max
        )[0]
        self.updateClippedRegions()

    @Slot(int)
    def updateDurationPadding(self, padding: int) -> None:
        """Slot called to update the time padding parameter (in ms) for calculating clipped regions

        Args:
            padding (int): value in milliseconds to draw the clipped region (or bunch clipped points together)
        """
        self.settings.clippingPaddingDuration = padding
        self.updateClippedRegions()

    def updateClippedRegions(self) -> None:
        self._generateQRects()
        if self.globalClippedRegions is not None:
            self.globalViewBox.removeItem(self.globalClippedRegions)
            self.globalClippedRegions = None
        if self.localClippedRegions is not None:
            self.localViewBox.removeItem(self.localClippedRegions)
            self.localClippedRegions = None

        if self.clippedRects:
            self.globalClippedRegions = ClippedRegions(
                self.clippedRects, self.settings.clippingColor
            )
            self.localClippedRegions = ClippedRegions(
                self.clippedRects, self.settings.clippingColor
            )
            self.globalViewBox.addItem(self.globalClippedRegions)
            self.localViewBox.addItem(self.localClippedRegions)

    def _generateQRects(
        self,
    ) -> None:
        if self.wave is None:
            return None
        padding = (self.settings.clippingPaddingDuration / 1000) * self.wave.fs
        height = self.wave.max - self.wave.min
        top = self.wave.max
        width = padding * 2
        self.clippedRects.clear()
        for index in self.clippedIndexes.tolist():
            left = index - padding
            self.clippedRects.append(QRectF(left, top, width, -height))
        return None

    def determineClippedRegions(self) -> None:
        self.determineClippedIndexes()
