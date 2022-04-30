from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QPointF, Slot
from qtpy.QtWidgets import QApplication

if TYPE_CHECKING:
    from typing import Any, Optional

    from qtpy.QtCore import QEvent
    from signalworks.tracking import Wave

    from barney.controllers.PlotController import PlotController
    from barney.views.PlotArea import PlotView

logger = logging.getLogger(__name__)


class LogEnergyPlot(pg.PlotItem):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.vb.setMouseEnabled(x=False, y=False)
        self.vb.setMenuEnabled(False)
        self.logEnergyPlot: Optional[pg.PlotCurveItem] = None
        self.hideButtons()
        self.hideAxis("left")
        self.hideAxis("bottom")

        self.vb.name = "Log Energy Plot"

        # info box
        self.logEnergyInfo = pg.TextItem(
            "", anchor=(0, 0), fill=(127, 127, 127, 127), color=(255, 255, 255)
        )
        self.logEnergyInfo.setFont(QApplication.instance().infoFont)  # noqa
        self.logEnergyInfo.setZValue(30)
        self.logEnergyInfo.setParentItem(self.vb)
        self.logEnergyInfo.setPos(QPointF(10, 10))
        self.logEnergyInfo.hide()

        # vertical Line
        self.verticalLine = pg.InfiniteLine(angle=90, movable=False)
        self.verticalLine.hide()
        self.verticalLine.setZValue(1e9)
        self.verticalLine.setParentItem(self.vb)

    @Slot()
    def waveformPlotted(self) -> None:
        self.vb.clear()
        if self.scene() is None:
            logger.warning("Log Energy Plot not in scene")
            return None
        self.scene().sigMouseMoved.connect(self.invokeLogEnergyTooltip)

        self.verticalLine.show()
        self.verticalLine.setPos(self.plotView.lastPosition.x())
        self.logEnergyPlot = pg.PlotCurveItem()
        self.addItem(self.logEnergyPlot)
        self.vb.setRange(
            yRange=(
                self.plotController.specController.settings.specLow,
                self.plotController.specController.settings.specHigh,
            ),
            padding=0.0,
        )
        return None

    @Slot(object)
    def updateEnergyPlot(self, frames: np.ndarray) -> None:
        if not QApplication.instance().settings._showLogEnergy:  # noqa
            # don't do the calcaulation...
            return None
        y = 10 * np.log10(
            np.mean(np.square(frames), axis=1) + np.finfo(frames.dtype).eps
        )
        if self.logEnergyPlot is None:
            return None
        self.logEnergyPlot.setData(y=y, padding=0.0)
        self.vb.setRange(xRange=(0, len(y) - 1), padding=0.0, update=True)
        return None

    @property
    def plotView(self) -> PlotView:
        return self.parent().getViewWidget()

    @property
    def selectionRegion(self) -> pg.LinearRegionItem:
        return self.plotView.selectionRegion

    @property
    def localViewBox(self) -> pg.ViewBox:
        return self.plotView.zoomPlot.vb

    @property
    def plotController(self) -> PlotController:
        return self.plotView.plotController

    @property
    def wave(self) -> Wave:
        return self.plotView.wave

    @Slot(object)
    def invokeLogEnergyTooltip(self, event: QEvent) -> None:
        if self.wave is None or self.logEnergyPlot is None or not self.isVisible():
            return None

        if self.sceneBoundingRect().contains(event):
            self.logEnergyInfo.show()
            xIndex = self.vb.mapSceneToView(event).toPoint().x()
            y = self.logEnergyPlot.yData[xIndex]
            time = self.plotView.spectrogram.spectrogramTime[int(event.x())]

            energyString = "Energy:"
            timeString = "Time:"
            minString = "Local Min:"
            maxString = "Local Max:"
            textInfo = (
                f"{energyString:>10} {y:.3} db \n"
                + f"{minString:>10} {self.logEnergyPlot.yData.min():.3} db \n"
                + f"{maxString:>10} {self.logEnergyPlot.yData.max():.3} db \n"
                + f"{timeString:>10} {int(1_000 * time / self.wave.fs):,} ms"
            )
            self.logEnergyInfo.setText(textInfo)
        else:
            self.logEnergyInfo.hide()
        return None
