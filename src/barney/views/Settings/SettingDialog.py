from __future__ import annotations

from contextlib import suppress
from enum import IntEnum, auto
from typing import TYPE_CHECKING

import sounddevice as sd
from qtpy.QtWidgets import QDialog, QTabWidget, QVBoxLayout

from barney.views.Settings.WaveformSettings import WaveformSettings

from .AudioSettings import AudioSettings
from .FontSettings import FontSettings
from .SpectrogramSettings import SpectrogramSettings

if TYPE_CHECKING:
    from ..MainWindow import MainWindow


class TabEnum(IntEnum):
    spec = 0
    am = auto()
    wave = auto()
    audio = auto()
    font = auto()


class SettingDialog(QDialog):
    def __init__(self, parent: MainWindow) -> None:
        super().__init__(parent)
        self.mainWindow = parent
        self.resize(600, 400)

        self.tabWidget = QTabWidget(self)

        self.specTab = SpectrogramSettings(self.tabWidget, self, TabEnum.spec)
        self.waveTab = WaveformSettings(self.tabWidget, self, TabEnum.wave)
        with suppress(sd.PortAudioError):
            self.audioTab = AudioSettings(self.tabWidget, self, TabEnum.audio)
        self.fontTab = FontSettings(self.tabWidget, self, TabEnum.font)
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabWidget)
        self.setLayout(layout)
