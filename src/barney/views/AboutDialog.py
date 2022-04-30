from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QDialog, QLabel, QVBoxLayout

from barney.__version__ import version

if TYPE_CHECKING:
    from .MainWindow import MainWindow


class AboutDialog(QDialog):
    def __init__(self, parent: MainWindow, tag: str) -> None:
        super().__init__(parent)
        mainLayout = QVBoxLayout(self)
        self.tag = tag

        spiel = QLabel("Barney: data review tool", self)
        versionLabel = QLabel(f"{version}", self)
        copyright = QLabel("Copyright 2019 Sensory, Inc.", self)

        mainLayout.addWidget(spiel)
        mainLayout.addWidget(versionLabel)
        mainLayout.addWidget(copyright)

        self.setWindowTitle("About")
        self.setLayout(mainLayout)
