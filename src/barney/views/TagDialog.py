from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from .MainWindow import MainWindow

logger = logging.getLogger(__name__)


class TagDialog(QDialog):
    def __init__(self, parent: MainWindow, tag: str) -> None:
        super().__init__(parent)

        mainLayout = QVBoxLayout(self)
        self.tag = tag
        reasons: List[str]
        if tag == "skip":
            reasons = sorted(
                [
                    "Background Noise",
                    "Clipping/Saturation",
                    "Digitization Artifact",
                    "Dropped Frames",
                    "Duplicate Speaker",
                    "Empty Waveform",
                    "Equipment Problem",
                    "Inappropriate Noise",
                    "Long Pauses",
                    "Muffled",
                    "Noise Cancelling",
                    "Non-native",
                    "Odd/Dramatic Speech",
                    "Prompt/Audio Mismatch",
                    "Truncation",
                    "TTS speech",
                    "Wrong Demographic",
                ]
            )
            reasons.insert(0, "Other")
        elif tag == "flag":
            reasons = ["Other"]
        else:
            raise ValueError(f"tag {tag} not recognized")

        reason = QLabel("Reason", self)
        self.reason = QComboBox(self)
        self.reason.addItems(reasons)
        reason.setBuddy(self.reason)

        comment = QLabel("Comment", self)
        self.comment = QLineEdit(self)
        comment.setBuddy(comment)

        self.buttonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self
        )
        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.close)
        grid = QGridLayout()
        grid.addWidget(reason, 0, 0)
        grid.addWidget(self.reason, 0, 1)
        grid.addWidget(comment, 1, 0)
        grid.addWidget(self.comment, 1, 1)

        mainLayout.addLayout(grid)
        mainLayout.addWidget(self.buttonBox)

        self.setWindowTitle("Tag Dialog")
        self.setLayout(mainLayout)
        self.comment.setFocus()

    @Slot()
    def onAccept(self) -> None:
        logger.debug("Tag dialog accepted")
        form = {"reason": self.reason.currentText(), "comment": self.comment.text()}
        self.parent()._controller.audioTagController.addToDatabase(
            self.parent().selectedIndexes(), form, self.tag
        )
        self.close()
