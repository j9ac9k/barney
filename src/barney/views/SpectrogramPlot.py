from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QPointF, QRect, Slot
from qtpy.QtWidgets import QApplication

if TYPE_CHECKING:
    from typing import Any, Optional, Tuple

    from qtpy.QtCore import QEvent
    from signalworks.tracking import Wave

    from barney.controllers.PlotController import PlotController

    from ..controllers.SubPlotControllers.SpectrogramController import (
        SpectrogramController,
    )

logger = logging.getLogger(__name__)


class Spectrogram(pg.ViewBox):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(name="Spectrogram", *args, **kwargs)

        self.f: np.ndarray = np.array([])
        self.X: np.ndarray = np.array([])

        self.sigResized.connect(self.calculateFrequencyArray)
        self.sigResized.connect(lambda _: self.updateSpectrogram(self.region))

        # Image
        self.image = pg.ImageItem()
        self.addItem(self.image)

        # crosshairs
        self.verticalLine = pg.InfiniteLine(angle=90, movable=False)
        self.horizontalLine = pg.InfiniteLine(angle=0, movable=False)
        self.verticalLine.hide()
        self.horizontalLine.hide()
        self.verticalLine.setZValue(1e9)
        self.horizontalLine.setZValue(1e9)
        self.verticalLine.setParentItem(self)
        self.addItem(self.horizontalLine)

        # text bos
        self.spectrogramInfo = pg.TextItem(
            "", anchor=(0, 0), fill=(127, 127, 127, 185), color=(255, 255, 255)
        )
        self.spectrogramInfo.setFont(QApplication.instance().infoFont)  # noqa
        self.spectrogramInfo.setZValue(30)
        self.spectrogramInfo.setParentItem(self)
        self.spectrogramInfo.setPos(QPointF(10, 10))
        self.spectrogramInfo.hide()

    @Slot(object)
    def calculateFrequencyArray(self) -> None:
        if self.image.image is not None:
            self.f = np.linspace(0, self.wave.fs // 2, num=self.image.height())

    @Slot(object)
    def invokeSpectrogramTooltip(self, event: QEvent) -> None:
        if self.wave is None or self.X is None or self.f is None:
            self.horizontalLine.hide()
            return None

        if self.sceneBoundingRect().contains(event):
            mousePoint = self.mapSceneToView(event)

            self.horizontalLine.setPos(mousePoint.y())
            self.horizontalLine.show()

            sample = self.spectrogramTime[int(event.x())]
            frequency = self.f[int(mousePoint.y())]

            energyString = "Energy:"
            timeString = "Time:"
            sampleString = "Sample:"
            freqString = "Frequency:"

            toolTipText = (
                f"{energyString:>10} {self.X[int(mousePoint.x()), int(mousePoint.y())]:.3} dB \n"
                + f"{timeString:>10} {int(1_000 * sample / self.wave.fs):,} ms\n"
                + f"{sampleString:>10} {sample:,}\n"
                + f"{freqString:>10} {int(frequency):,} Hz"
            )
            self.spectrogramInfo.setText(toolTipText)
            self.spectrogramInfo.show()
        else:
            self.horizontalLine.hide()
            self.spectrogramInfo.hide()
        return None

    @property
    def wave(self) -> Wave:
        return self.parent().getViewWidget().wave

    @property
    def plotController(self) -> PlotController:
        return self.parent().getViewWidget().plotController

    @property
    def spectrogramController(self) -> SpectrogramController:
        return self.plotController.specController

    @Slot(np.ndarray)
    def colorSpectrogram(self, lookUpTable: np.ndarray) -> None:
        self.image.setLookupTable(lookUpTable)

    @Slot(int, int)
    def clipSpectrogram(self, low: int, high: int) -> None:
        """Function called to clip spectrogram.  Both inputs are integers between 0 and 100

        Parameters
        ----------
        low : int
            Percentage to clip the lower end of the spectogram to
            0 <= low < high
        high : int
            Percentage to clip the upper end of the spectogram to
            low < high <= 100
        """
        if self.X is not None:
            levelOptions = np.linspace(self.X.min(), self.X.max(), 101)
            levels = [levelOptions[low], levelOptions[high]]
            self.image.setLevels(levels)

    @Slot(object)
    def updateSpectrogram(self, _: Optional[pg.LinearRegionItem] = None) -> None:
        if self.getViewWidget() is None or self.wave is None:
            self.horizontalLine.hide()
            self.verticalLine.hide()
        else:
            height = self.boundingRect().height()
            self.spectrogramController.newSpectrogramArray(height)
        return None

    def updateLineColor(self) -> None:
        self.horizontalLine.setPen(self.spectrogramController.spectrogramLineColor)
        self.verticalLine.setPen(self.spectrogramController.spectrogramLineColor)

    @property
    def spectrogramTime(self) -> np.ndarray:
        region: Tuple[float, float] = self.region.getRegion()
        if region is not None:
            return np.linspace(*region, int(self.width()), dtype=int)
        else:
            raise RuntimeError("Selection Region Somehow Unavailable")

    @property
    def region(self) -> pg.LinearRegionItem:
        return self.getViewWidget().region

    @Slot(object)
    def newSpectrogramImage(self, result: Tuple[np.ndarray, np.ndarray]) -> None:
        if self.wave is None:
            return None
        self.verticalLine.show()
        self.spectrogramController.applyColorMap()

        X, f = result
        cutoffFreq = min(self.wave.fs // 2, self.spectrogramController.freqCutoff)
        if self.spectrogramController.enableFreqCutoff:
            index = np.searchsorted(f, cutoffFreq, side="right")
            self.X = X[:, :index]
            self.f = f[:index]
        else:
            self.X = X
            self.f = f

        self.setRange(QRect(0, 0, *self.X.shape), padding=0.0)
        pg.functions.clip_array(self.X, 0, None, out=self.X)
        if X.shape[0]:
            self.image.setImage(image=self.X, padding=0.0, levels=(X.min(), X.max()))

        self.show()
        self.scene().sigMouseMoved.connect(self.invokeSpectrogramTooltip)

    def clearPlot(self) -> None:
        # handle spectrogram threads
        controller = self.spectrogramController
        controller.queuedThread = None
        if controller.currentThread is not None and controller.metaObjects is not None:
            for metaObject in controller.metaObjects:
                controller.currentThread.disconnect(metaObject)
        self.image.clear()

    @property
    def lowClipping(self) -> int:
        return self.plotController.specController.lowCap

    @property
    def highClipping(self) -> int:
        return self.plotController.specController.highCap
