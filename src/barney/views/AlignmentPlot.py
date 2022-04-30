from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

import numpy as np
import pyqtgraph as pg
from qtpy.QtCore import QPointF
from signalworks.tracking import Partition

from barney.Utilities.ParseAlignments import parseAlignmentFields

if TYPE_CHECKING:
    from typing import Any, Dict, List, Optional

    from qtpy.QtGui import QFont
    from signalworks.tracking import Wave

    from barney.Utilities.ParseAlignments import Alignment
    from barney.views.PlotArea import PlotView

logger = logging.getLogger(__name__)


class AlignmentPlots(pg.GraphicsLayout):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.setSpacing(0)
        self.setContentsMargins(0, 0, 0, 0)
        self.verticalLines: List[pg.InfiniteLine] = []

    def clearPlot(self) -> None:
        self.clear()
        self.verticalLines.clear()

    def plotAlignments(self) -> None:
        profiler = pg.debug.Profiler(disabled=True, delayed=False)
        data = self.parent().getViewWidget().mainWindow.currentDatabaseEntry()
        profiler("Retrieved data")
        alignmentData = parseAlignmentFields(data)
        profiler("Parsed Alignment Fields")
        partitions = self._generateParitionTracks(alignmentData)
        profiler("Generated Partitions")
        for partition in partitions:
            self._plotPartition(partition)
            self.nextRow()
        profiler("Finished Setting Partitions")
        self.setFixedHeight(30 * len(self.items))
        profiler("Set Fixed Height")
        self.parent().addItem(self, row=self.plotView.rowMapping["alignments"], col=0)
        profiler("Added myself a second time...")
        # self.show()

    def _generateParitionTracks(
        self, data: Dict[str, List[Alignment]]
    ) -> List[Partition]:
        tracks = []
        # TODO: skipped variable contains the name of the alignment field (eg: words, phones, states)
        # Barney should indicate the name of the field someplace...
        for _, partitions in data.items():
            partitionData = [
                (
                    partitionValue[0] / 1_000,
                    partitionValue[1] / 1_000,
                    partitionValue[2],
                )
                for partitionValue in partitions
            ]
            tracks.append(Partition.create(partitionData, fs=self.wave.fs))
        return tracks

    def _plotPartition(self, partition: Partition) -> None:
        profiler = pg.debug.Profiler(disabled=True, delayed=False)
        with suppress(Exception):
            self.parent().removeItem(self)
        profiler("Removed self from parent")
        viewBox = pg.ViewBox(
            border=(255, 255, 255), enableMouse=False, enableMenu=False
        )
        profiler("Created Viewbox")

        regions = []
        textItems = []

        for label, start, end in zip(
            partition.value, partition.time[:-1], partition.time[1:]
        ):
            if label == "":
                continue
            region = pg.LinearRegionItem(values=(start, end), movable=False)
            region.setParentItem(viewBox.childGroup)
            regions.append(region)
            profiler("Created Region")

            textItem = pg.TextItem(text=label, color=(255, 255, 255), anchor=(0.5, 0.5))
            textItem.setPos(QPointF(np.mean([start, end]), 0.5))
            textItem.setParentItem(viewBox.childGroup)
            textItems.append(textItem)
            profiler("Created Text Item")
        profiler("Finished For Loop")

        font = self.suggestedFont()
        if font is not None:
            for item in textItems:
                item.setFont(font)

        viewBox.addedItems.extend(regions + textItems)
        verticalLine = pg.InfiniteLine(angle=90, movable=False)
        verticalLine.setParentItem(viewBox)
        self.verticalLines.append(verticalLine)
        profiler("Added Vertical Line")
        viewBox.setXRange(*self.selectedRegion.getRegion(), padding=0.0)
        viewBox.setYRange(0, 1, padding=0.0)
        viewBox.setLimits(xMin=0, yMin=0, yMax=1)
        viewBox.setXLink(self.localViewBox)
        self.addItem(viewBox, col=0)
        profiler("Added viewbox to layout")

    def setFont(self, font: QFont) -> None:
        for viewBox in self.items.keys():
            if isinstance(viewBox, pg.ViewBox):
                for textItem in filter(
                    lambda x: isinstance(x, pg.TextItem), viewBox.addedItems
                ):
                    textItem.setFont(font)

    def suggestedFont(self) -> Optional[QFont]:
        """
        If the Font Controller is storing a valid font to render, use that,
        otherwise return None
        """
        font = self.plotView.plotController.fontController.alignmentFont()
        if font.pixelSize() == -1 and font.pointSize() == -1:
            # font is invalid/default value
            return None
        return font

    @property
    def plotView(self) -> PlotView:
        return self.parent().getViewWidget()

    @property
    def wave(self) -> Wave:
        return self.plotView.wave

    @property
    def localViewBox(self) -> pg.ViewBox:
        return self.plotView.zoomPlot.vb

    @property
    def selectedRegion(self) -> pg.LinearRegionItem:
        return self.plotView.mainPlot.selectionRegion
