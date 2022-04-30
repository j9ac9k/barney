from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qtpy.QtCore import QObject

if TYPE_CHECKING:
    from signalworks import Wave

    from ...views.PlotArea import PlotView
    from ..controller import MainController
    from ..PlotController import PlotController


logger = logging.getLogger(__name__)


class SubPlotController(QObject):
    def __init__(self, parent: PlotController) -> None:
        if type(self) is SubPlotController:
            raise ValueError("SubPlotController must be subclassed.")
        super().__init__(parent)
        self.plotController = parent

    @property
    def plotView(self) -> PlotView:
        return self.plotController.plotView

    @property
    def wave(self) -> Wave:
        return self.plotController.wave

    @property
    def mainController(self) -> MainController:
        return self.plotController.mainController

    def refreshAllPlots(self) -> None:
        self.plotController.plotView.plotWaveform()

    def refreshSubPlot(self) -> None:
        raise NotImplementedError
