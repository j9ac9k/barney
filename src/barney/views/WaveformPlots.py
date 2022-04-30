from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QPointF, QRectF, Qt, Slot
from qtpy.QtWidgets import QApplication

from barney.controllers.SubPlotControllers.WaveformController import WaveformController
from barney.Utilities.BlockSignals import BlockSignals

if TYPE_CHECKING:
    from typing import Any

    from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent, MouseDragEvent
    from qtpy.QtCore import QEvent
    from signalworks.tracking import Wave

    from barney.controllers.PlotController import PlotController
    from barney.views.PlotArea import PlotView


logger = logging.getLogger(__name__)


class GlobalPlot(pg.PlotItem):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.vb.name = "Global Plot"

        self.setTitle("Waveform")
        self.hideAxis("left")
        self.hideAxis("bottom")

        self.selectionRegion = pg.LinearRegionItem(
            pen={"color": "#7E57C2", "width": 2},
            hoverPen={"color": "#F4511E", "width": 2},
        )
        self.selectionRegion.setZValue(1e9)
        self.selectionRegion.setMovable(True)

        self.vb.mouseDragEvent = self.mouseDragEvent
        self.selectionRegion.mouseDragEvent = self.mouseDragEvent

        self.globalVerticalLine = pg.InfiniteLine(angle=90, movable=False)
        self.globalVerticalLine.hide()
        self.globalVerticalLine.setZValue(10)

        self.shrugItem = pg.TextItem(
            html=(
                '<div style="text-align: center; color: white">'
                '<span style="font-size: 32pt;">'
                r"¯\_(ツ)_/¯"
                "</span>"
                "</div>"
            ),
            anchor=(0.5, 0.5),
        )
        self.shrugItem.hide()
        self.vb.addItem(self.shrugItem)
        self.shrugItem.setPos(0.5, 0.5)

        # Info box
        self.globalWaveformInfo = pg.TextItem(
            "", anchor=(0, 0), fill=(127, 127, 127, 127), color=(255, 255, 255)
        )
        self.globalWaveformInfo.setZValue(30)
        self.globalWaveformInfo.setFont(QApplication.instance().infoFont)  # noqa
        self.globalWaveformInfo.hide()
        self.globalWaveformInfo.setParentItem(self.vb)
        self.globalWaveformInfo.setPos(QPointF(10, 3))

    @property
    def plotView(self) -> PlotView:
        return self.parent().getViewWidget()

    @property
    def plotController(self) -> PlotController:
        return self.plotView.plotController

    @property
    def wave(self) -> Wave:
        return self.plotView.wave

    @property
    def waveController(self) -> WaveformController:
        return self.plotController.waveController

    @Slot(object)
    def invokeWaveformTooltip(self, event: QEvent) -> None:
        if self.wave is None:
            return None
        if self.vb.sceneBoundingRect().contains(event):
            toolTipText = self.waveController.waveformInfoText()
            self.globalWaveformInfo.setText(toolTipText)
            self.globalWaveformInfo.show()
        else:
            self.globalWaveformInfo.hide()

    @Slot()
    def plotWaveform(self) -> None:
        self.vb.prepareForPaint()
        self.vb.setMouseEnabled(x=False, y=False)
        upperLimit = len(self.wave._value) - 1 + self.wave._offset
        absMax = np.abs(self.wave.value).max()
        self.vb.setRange(
            rect=QRectF(QPointF(0, absMax), QPointF(upperLimit, -absMax)),
            padding=np.finfo(float).eps,
        )
        x, y = self.waveController.calcPlottableWaveform(self.wave)
        waveformPlot = self.plot(x=x, y=y)
        waveformPlot.setDownsampling(auto=True, method="peak")
        self.vb.addItem(self.globalVerticalLine)
        self.globalVerticalLine.show()

        self.addItem(self.selectionRegion)
        with BlockSignals(self.selectionRegion):
            self.selectionRegion.setBounds((0, upperLimit))
            self.selectionRegion.setRegion(np.array([0.0, 1.0]) * upperLimit)

        # firing signal (one time)
        self.selectionRegion.sigRegionChanged.emit(self.selectionRegion)
        self.vb.scene().sigMouseMoved.connect(self.invokeWaveformTooltip)

    def clear(self) -> None:
        self.shrugItem.hide()
        self.removeItem(self.selectionRegion)
        # self.vb.scene().sigMouseMoved.disconnect(self.invokeWaveformTooltip)
        self.vb.clear()
        self.vb.addItem(self.shrugItem)

    def mouseDragEvent(self, ev: QEvent) -> None:
        ev.accept()
        if ev.button() & (Qt.LeftButton | Qt.MidButton):
            positions = sorted(
                map(self.vb.mapSceneToView, (ev.buttonDownScenePos(), ev.scenePos())),
                key=QPointF.x,
            )
            with BlockSignals(self.selectionRegion):
                self.selectionRegion.setRegion(positions)
            self.selectionRegion.sigRegionChanged.emit(self.selectionRegion)


class LocalPlot(pg.PlotItem):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.hideButtons()
        self.hideAxis("left")
        self.hideAxis("bottom")

        self.vb.mouseDragEvent = self.mouseDragEvent
        self.vb.mouseClickEvent = self.viewboxMouseClickEvent
        self.vb.name = "Local Waveform"

        # Audio Region
        self.playbackRegion = pg.LinearRegionItem(
            brush=pg.mkBrush("#C6FF002A"), hoverBrush=pg.mkBrush("#C6FF007F")
        )
        self.playbackRegion.hide()
        self.playbackRegion.mouseDragEvent = self.mouseDragEvent
        self.playbackRegion.mouseClickEvent = self.regionMouseClickEvent
        self.playbackRegion.setZValue(1e10)
        self.playbackRegion.setMovable(True)

        # Playback Location Line
        self.playbackLocation = pg.InfiniteLine(angle=90, movable=False)
        self.playbackLocation.hide()
        self.vb.addItem(self.playbackLocation)

        # Info box
        self.localWaveformInfo = pg.TextItem(
            "", anchor=(0, 0), fill=(127, 127, 127, 127), color=(255, 255, 255)
        )
        self.localWaveformInfo.setZValue(30)
        self.localWaveformInfo.setFont(QApplication.instance().infoFont)  # noqa
        self.localWaveformInfo.hide()
        self.localWaveformInfo.setParentItem(self.vb)
        self.localWaveformInfo.setPos(QPointF(10, 10))

        # Vertical Line
        self.verticalLine = pg.InfiniteLine(angle=90, movable=False)
        self.verticalLine.hide()
        self.vb.addItem(self.verticalLine)

    # def clearPlot(self) -> None:
    #     self.vb.scene().sigMouseMoved.disconnect(self.invokeWaveformTooltip)
    #     self.clear()

    def clear(self) -> None:
        self.playbackRegion.hide()
        super().clear()

    def plotWaveform(self) -> None:
        self.updateView(self.selectionRegion)
        self.vb.show()
        self.vb.setMouseEnabled(x=False, y=False)
        self.verticalLine.show()

        x, y = self.waveController.calcPlottableWaveform(self.wave)
        plot = self.plot(x=x, y=y)
        plot.setDownsampling(auto=True, method="peak")
        self.addItem(self.playbackRegion)
        self.vb.scene().sigMouseMoved.connect(self.invokeWaveformTooltip)

    @Slot(object)
    def updateView(self, selectionRegion: pg.LinearRegionItem) -> None:
        self.vb.prepareForPaint()
        self.vb.setRange(
            xRange=selectionRegion.getRegion(),
            yRange=[self.wave.min, self.wave.max],
            padding=0.0,
            update=True,
        )
        return None

    @property
    def wave(self) -> Wave:
        return self.getViewWidget().wave

    @property
    def plotController(self) -> PlotController:
        return self.getViewWidget().plotController

    @property
    def selectionRegion(self) -> pg.LinearRegionItem:
        return self.getViewWidget().mainPlot.selectionRegion

    @property
    def waveController(self) -> WaveformController:
        return self.plotController.waveController

    @Slot(object)
    def invokeWaveformTooltip(self, event: QEvent) -> None:
        if self.wave is None:
            return None
        if self.vb.sceneBoundingRect().contains(event):
            mousePoint = self.vb.mapSceneToView(event)
            sample = int(mousePoint.x())
            toolTipText = self.waveController.toolTipText(sample)
            self.localWaveformInfo.setText(toolTipText)
            self.localWaveformInfo.show()
        else:
            self.localWaveformInfo.hide()

    def mouseDragEvent(self, ev: MouseDragEvent) -> None:
        ev.accept()
        if ev.button() & (Qt.LeftButton | Qt.MidButton):
            if ev.isStart():
                self.stopPlayback()
                self.playbackRegion.show()
            positions = sorted(
                map(self.vb.mapSceneToView, (ev.buttonDownScenePos(), ev.scenePos())),
                key=QPointF.x,
            )
            self.playbackRegion.setRegion(positions)
        return None

    def viewboxMouseClickEvent(self, ev: MouseClickEvent) -> None:
        ev.accept()
        if ev.button() == Qt.RightButton:
            self.stopPlayback()
        return None

    def regionMouseClickEvent(self, ev: MouseClickEvent) -> None:
        ev.accept()
        if ev.button() == Qt.RightButton:
            self.stopPlayback()
        else:
            self.getViewWidget().clickPlay(ev)
        return None

    def stopPlayback(self) -> None:
        self.playbackRegion.hide()
        self.playbackLocation.hide()
        self.plotController.parent().sigStopRequested.emit()
