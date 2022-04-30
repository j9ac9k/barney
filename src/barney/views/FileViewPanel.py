from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from .ListView import ListView

if TYPE_CHECKING:
    from .HorizontalSplitter import HorizontalSplitter


class Pane(QWidget):
    def __init__(self, parent: HorizontalSplitter) -> None:
        super().__init__(parent)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(3, 3, 3, 3)

        self.textInput = QLineEdit(self)
        self.textInput.setClearButtonEnabled(True)
        self.textInput.setPlaceholderText("e.g.: order:ASC snr:>5")
        self.listView = ListView(self)

        layout.addWidget(self.textInput, 0)
        layout.addWidget(self.listView, 1)

        self.setLayout(layout)
