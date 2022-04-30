from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtGui import QFont
from qtpy.QtWidgets import QFontDialog, QPushButton, QSizePolicy, QTextEdit

from .SettingsTab import SettingsTab

if TYPE_CHECKING:
    from typing import Any

    from barney.controllers.SubPlotControllers.FontController import FontController

logger = logging.getLogger(__name__)


class FontSettings(SettingsTab):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Render Font Settings"""
        super().__init__("Font", *args, **kwargs)
        self.fontController = self.plotController.fontController
        self.alignmentTextEdit = QTextEdit(self)
        self.alignmentTextEdit.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        self.alignmentFontDialog = QFontDialog(self)
        self.alignmentFontDialog.currentFontChanged.connect(self.setAlignmentFont)
        self.alignmentFontButton = QPushButton("Select Alignment Font")
        self.alignmentFontButton.clicked.connect(self.showAlignmentFontDialog)

        self.transcriptionTextEdit = QTextEdit(self)
        self.transcriptionTextEdit.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )

        self.transcriptionFontDialog = QFontDialog(self)
        self.transcriptionFontDialog.currentFontChanged.connect(
            self.setTranscriptionFont
        )
        self.transcriptionFontButton = QPushButton("Select Transcription Font")
        self.transcriptionFontButton.clicked.connect(self.showTranscriptionFontDialog)

        self.gridLayout.setRowStretch(0, 100)
        self.gridLayout.setColumnStretch(0, 100)
        self.gridLayout.setColumnStretch(1, 100)

        # we don't use column 2 in this setting
        self.gridLayout.setColumnStretch(2, 0)

        self.gridLayout.addWidget(self.alignmentTextEdit, 0, 0)
        self.gridLayout.addWidget(
            self.alignmentFontButton, 1, 0, alignment=Qt.AlignRight
        )

        self.gridLayout.addWidget(self.transcriptionTextEdit, 0, 1)
        self.gridLayout.addWidget(
            self.transcriptionFontButton, 1, 1, alignment=Qt.AlignRight
        )

    def showAlignmentFontDialog(self) -> None:
        self.alignmentFontDialog.open()

    def showTranscriptionFontDialog(self) -> None:
        self.transcriptionFontDialog.open()

    def setAlignmentFont(self, font: QFont) -> None:
        self.alignmentTextEdit.setFont(font)
        self.configManager.setAlignmentFont(font)

    def setTranscriptionFont(self, font: QFont) -> None:
        self.transcriptionTextEdit.setFont(font)
        self.configManager.setTranscriptionFont(font)

    @property
    def configManager(self) -> FontController:
        return self.fontController
