from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, Optional

import pyqtgraph as pg
from qtpy.QtCore import QEvent, QObject, QPointF, Qt, Signal, Slot
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QApplication, QSizePolicy
from signalworks import tracking

from barney.controllers.PlotController import PlotController
from barney.views.AlignmentPlot import AlignmentPlots
from barney.views.LogEnergyPlot import LogEnergyPlot
from barney.views.SpectrogramPlot import Spectrogram
from barney.views.WaveformPlots import GlobalPlot, LocalPlot

if TYPE_CHECKING:
    from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent

    from .MainWindow import MainWindow


logger = logging.getLogger(__name__)


class PlotView(pg.GraphicsView):

    sigPlotWaveformFinished = Signal()

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.mainWindow: MainWindow = self.parent().parent()
        self.plotController: PlotController = self.mainWindow._controller.plotController
        self.plotController.plotView = self
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.lastPosition: QPointF = QPointF(0.0, 0.0)

        self.rowMapping: Dict[str, int] = {
            "globalWaveform": 0,
            "localWaveform": 1,
            "logEnergy": 2,
            "spectrogram": 3,
            "alignments": 4,
            "transcription": 5,
        }

        self.setContentsMargins(0, 0, 0, 0)

        # generic layout
        self.layout = pg.GraphicsLayout()
        self.setCentralItem(self.layout)
        self.scene().sigMouseMoved.connect(self.setVerticalLines)
        self.scene().sigMouseClicked.connect(self.mouseClicked)
        self.layout.setSpacing(3)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.layout.setColumnStretchFactor(0, 100)

        #####################
        #  Global waveform view
        #####################
        self.mainPlot: GlobalPlot = GlobalPlot(enableMenu=True)
        self.mainPlot.setParent(self.layout)
        self.layout.addItem(
            self.mainPlot.vb, row=self.rowMapping["globalWaveform"], col=0
        )
        self.layout.layout.setRowFixedHeight(self.rowMapping["globalWaveform"], 75)

        #####################
        #  local waveform view
        #####################
        self.zoomPlot: LocalPlot = LocalPlot(enableMenu=False)
        self.zoomPlot.setParent(self.layout)
        self.layout.addItem(self.zoomPlot, row=self.rowMapping["localWaveform"], col=0)
        self.layout.layout.setRowFixedHeight(self.rowMapping["localWaveform"], 150)

        #####################
        #  spectrogram view
        #####################
        self.spectrogram: Spectrogram = Spectrogram(enableMenu=False, enableMouse=False)
        self.spectrogram.setParent(self.layout)

        self.layout.addItem(self.spectrogram, row=self.rowMapping["spectrogram"], col=0)
        self.layout.layout.setRowStretchFactor(self.rowMapping["spectrogram"], 100)
        self.plotController.specController.sigApplyColorMap.connect(
            self.spectrogram.colorSpectrogram
        )

        #####################
        #  log Energy view
        #####################
        # we create the plot but don't show it unless needed
        self.logEnergyPlot: LogEnergyPlot = LogEnergyPlot()
        self.logEnergyPlot.setParent(self.layout)
        self.showLogEnergyPlot(QApplication.instance().settings._showLogEnergy)  # noqa

        #####################
        #  alignments
        #####################
        self.alignments = AlignmentPlots(parent=self.layout)
        self.alignments.setParent(self.layout)

        #####################
        #  transcription
        #####################
        self.defaultTranscriptionSize = (
            self.transcriptionSize
        ) = self.plotController.fontController.transcriptionFont().pointSizeF()
        self.transItem = self.layout.addLabel(
            "",
            row=self.rowMapping["transcription"],
            col=0,
        )

        font = self.plotController.fontController.transcriptionFont()
        self.setTranscriptionFont(font)
        self._connect()

    def _connect(self) -> None:
        self.plotController.showWaveform.connect(self.plotWaveform)
        self.plotController.showWaveform.connect(self.spectrogram.update)
        self.plotController.showWaveform.connect(self.logEnergyPlot.waveformPlotted)
        self.plotController.fileNotFound.connect(self.fileNotFoundPlot)

        # Audio Connetivity
        self.plotController.sigSetPlaybackPosition.connect(self.playbackLocation.setPos)
        self.plotController.parent().playbackController.sigPlaybackStopped.connect(
            lambda: self.zoomPlot.playbackLocation.hide()
        )
        self.plotController.parent().playbackController.sigPlaybackStarted.connect(
            lambda: self.zoomPlot.playbackLocation.show()
        )

        # Region Updating
        self.region.sigRegionChanged.connect(self.zoomPlot.updateView)
        self.region.sigRegionChangeFinished.connect(self.zoomPlot.updateView)
        self.region.sigRegionChanged.connect(self.spectrogram.updateSpectrogram)

        # Handling vertical line positioning when window is resized
        self.sigDeviceTransformChanged.connect(
            lambda x: x.setVerticalLines(x.lastPosition)
        )

        # Handle updating of fonts
        fontController = self.plotController.fontController
        fontController.sigTranscriptionFontChanged.connect(self.setTranscriptionFont)
        fontController.sigAlignmentFontChanged.connect(self.alignments.setFont)

    def setTranscriptionFont(self, font: QFont) -> None:
        if font.pixelSize() == -1 and font.pointSize() == -1:
            # font is invalid/default value
            newFont = self.transItem.item.font()
            self.plotController.fontController.setTranscriptionFont(newFont.toString())
            self.plotController.fontController.save
        else:
            self.transItem.item.setFont(font)

    def showLogEnergyPlot(self, show: bool) -> None:
        if show:
            self.layout.addItem(
                self.logEnergyPlot, row=self.rowMapping["logEnergy"], col=0
            )
            self.layout.layout.setRowFixedHeight(self.rowMapping["logEnergy"], 150)
            if self.wave is not None:
                self.logEnergyPlot.waveformPlotted()
        else:
            self.layout.layout.setRowFixedHeight(self.rowMapping["logEnergy"], 0)
        return None

    @property
    def region(self) -> pg.LinearRegionItem:
        return self.mainPlot.selectionRegion

    @property
    def playbackRegion(self) -> pg.LinearRegionItem:
        return self.zoomPlot.playbackRegion

    @property
    def playbackLocation(self) -> pg.InfiniteLine:
        return self.zoomPlot.playbackLocation

    @property
    def wave(self) -> tracking.Wave:
        return self.plotController.wave

    @Slot()
    def plotWaveform(self) -> None:
        profiler = pg.debug.Profiler(disabled=True, delayed=False)
        # TODO: hide and then show vertical lines after viewboxes have moved
        if self.wave is None:
            return
        # clean & plot global waveform
        self.clearTiers()
        profiler("Cleared Tiers")
        self.mainPlot.plotWaveform()
        profiler("Plotting global Plot")
        self.zoomPlot.plotWaveform()
        profiler("Plotted Local Plot")
        if QApplication.instance().settings._showLogEnergy:  # noqa
            self.logEnergyPlot.show()
            profiler("Plotted Log Energy")
        self.alignments.plotAlignments()
        profiler("Plotted Alignments")

        # render transcription
        self.updateTranscription()
        profiler("Updated Transcription")
        self.sigPlotWaveformFinished.emit()
        self.setVerticalLines(self.lastPosition)

    @Slot()
    def clearTiers(self) -> None:
        self.playbackLocation.hide()
        self.spectrogram.clearPlot()
        self.mainPlot.clear()
        self.zoomPlot.clear()
        self.logEnergyPlot.clear()
        self.transItem.setText("")
        self.alignments.clearPlot()
        self.layout.updateGeometry()

    @Slot()
    def fileNotFoundPlot(self) -> None:
        self.clearTiers()
        self.mainPlot.vb.setRange(
            xRange=(0, 1), yRange=(0, 1), padding=0.1, update=True
        )
        self.mainPlot.shrugItem.show()
        self.zoomPlot.vb.hide()  # why not hide the zoom plot?
        self.spectrogram.hide()

    def updateTranscription(self, change: Optional[str] = None) -> None:
        # update the raw transcription for a new selected item
        index = self.mainWindow.currentIndex()
        if not index.isValid():
            return None
        selection = self.mainWindow._model.fileProxyModel.currentSelection(index)
        if selection is None:
            return None
        text = selection["transcription"]
        if text == "nan":
            text = selection["orthography"]

        if change == "ResetText":
            self.transcriptionSize = self.defaultTranscriptionSize
        elif change == "IncreaseText":
            self.transcriptionSize += 1
        elif change == "DecreaseText":
            self.transcriptionSize = max(self.transcriptionSize - 1, 5)
        elif change is not None:
            logger.error(f"Received bogus change value {change}")

        # TODO: Use right-justification for rtl writing systems
        if text == "nan":  # check text is nan, it happens when loading audio files
            text = ""
            self.transItem.hide()
            return None

        self.transItem.show()
        columnWidth = self.width()
        self.transItem.setText(
            text=text, justify="left", size=f"{self.transcriptionSize}pt"
        )
        self.transItem.setFixedWidth(columnWidth)

    def resizeEvent(self, event: QEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "transItem"):
            self.transItem.setFixedWidth(self.width())
        return None

    def mouseClicked(self, event: MouseClickEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.clickPlay(event)
        return None

    def clickPlay(self, event: MouseClickEvent) -> None:
        for region in self.scene().items(event.scenePos()):
            if isinstance(region, pg.LinearRegionItem):
                minX, maxX = region.getRegion()
                self.playbackRegion.setRegion((minX, maxX))
                self.playbackRegion.show()
                self.playbackLocation.show()
                self.mainWindow.playAlignment(int(minX), int(maxX))
                event.accept()
                break
        return None

    @Slot(object)
    def setVerticalLines(self, position: QPointF) -> None:
        if self.wave is None:
            return None
        self.lastPosition = position
        localWaveformPoint = self.zoomPlot.vb.mapSceneToView(position)
        self.mainPlot.globalVerticalLine.setPos(localWaveformPoint.x())
        self.zoomPlot.verticalLine.setPos(localWaveformPoint.x())

        self.spectrogram.verticalLine.setPos(position.x())

        # due to off-by-one issue, using mapSceneToView
        if QApplication.instance().settings._showLogEnergy:  # noqa
            x = self.logEnergyPlot.vb.mapSceneToView(position).toPoint().x()
            self.logEnergyPlot.verticalLine.setPos(x)

        if self.alignments.isVisible():
            for alignmentLine in self.alignments.verticalLines:
                alignmentLine.setPos(position.x())
