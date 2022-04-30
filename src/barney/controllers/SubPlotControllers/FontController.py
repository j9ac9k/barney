from __future__ import annotations

import dataclasses
import logging
from typing import TYPE_CHECKING

from qtpy.QtCore import Signal
from qtpy.QtGui import QFont

from barney.Utilities.ConfigClass import ConfigClass

from .SubPlotController import SubPlotController

if TYPE_CHECKING:
    from ..PlotController import PlotController

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class FontControllerSettings(ConfigClass):

    alignmentFont: str = QFont().toString()
    transcriptionFont: str = QFont().toString()

    def __init__(self, config_key: str = ""):
        super().__init__(config_key)


class FontController(SubPlotController):

    sigTranscriptionFontChanged = Signal(QFont)
    sigAlignmentFontChanged = Signal(QFont)

    def __init__(self, parent: PlotController) -> None:
        super().__init__(parent)
        self.settings = FontControllerSettings(config_key="Font Options")

    @staticmethod
    def isValidFont(font: QFont) -> bool:
        """Determines if the QFont is valid for rendering by evaluating
        whether setPointSize or setPixelSize has been called on it with
        a positive value.  If neither have been called, then we can
        consider the font to be invalid

        Parameters
        ----------
        font : QFont
            font to be evaluated

        Returns
        -------
        bool
            whether the font has had a valid size set to it
        """
        return (font.pixelSize() == -1) ^ (font.pointSize() == -1)

    def setTranscriptionFont(self, font: QFont) -> None:
        old_font = self.transcriptionFont()
        if old_font != font:
            self.settings.transcriptionFont = font.toString()
            self.sigTranscriptionFontChanged.emit(font)

    def setAlignmentFont(self, font: QFont) -> None:
        old_font = self.alignmentFont()
        if old_font != font:
            self.settings.alignmentFont = font.toString()
            self.sigAlignmentFontChanged.emit(font)

    def transcriptionFont(self) -> QFont:
        font = QFont()
        font.fromString(self.settings.transcriptionFont)
        return font

    def alignmentFont(self) -> QFont:
        font = QFont()
        font.fromString(self.settings.alignmentFont)
        return font
