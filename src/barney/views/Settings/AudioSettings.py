from __future__ import annotations

import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING

import pyqtgraph as pg
import sounddevice as sd
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
)

from barney.Utilities.BlockSignals import BlockSignals

from ...controllers.PlaybackController import ExtraSounddeviceLogging
from .SettingsTab import SettingsTab

if TYPE_CHECKING:
    from typing import Any

    from barney.Utilities.ConfigClass import ConfigClass


logger = logging.getLogger(__name__)


class Rows(IntEnum):
    outputDevice = auto()
    playbackMechanism = auto()
    bufferSize = auto()
    test = auto()
    sdInfoDump = auto()


class AudioSettings(SettingsTab):
    Rows = Rows

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("Audio", *args, **kwargs)
        self.waveController = self.plotController.waveController
        self.playbackController = self.mainWindow._controller.playbackController

        # audio output device
        self._initAudioOutputDeviceSelection()

        # audio payback mechanism
        self._initAudioPlaybackMechanism()

        # set audio buffer
        self._initBufferSlider()

        # the log audio info button
        self._initSDInfoDumpBtn()

        # test audio button
        self._initTestAudioBtn()

    @property
    def configManager(self) -> ConfigClass:
        return self.waveController

    def _initAudioOutputDeviceSelection(self) -> None:
        self.outputDevices = QComboBox(self)
        label = QLabel("Audio Output Device", self)
        devices = [
            device for device in sd.query_devices() if device["max_output_channels"] > 0
        ]

        self.outputDevices.addItems([device["name"] for device in devices])
        self.outputDevices.setCurrentText(sd.query_devices(kind="output")["name"])

        self.outputDevices.currentTextChanged.connect(
            self.playbackController.setAudioDevice
        )

        self.gridLayout.addWidget(label, Rows.outputDevice, 0)
        self.gridLayout.addWidget(self.outputDevices, Rows.outputDevice, 1)

    def _initAudioPlaybackMechanism(self) -> None:
        playbackLabel = QLabel("Audio Playback Methods")
        buttonGroup = QButtonGroup(self)
        standardPlayback = QRadioButton("Standard", self)
        simplePlayback = QRadioButton("Simple", self)
        buttonGroup.addButton(standardPlayback)
        buttonGroup.addButton(simplePlayback)
        standardPlayback.setChecked(True)

        standardPlayback.toggled.connect(self.playbackMechanismChanged)
        simplePlayback.toggled.connect(self.playbackMechanismChanged)

        self.gridLayout.addWidget(playbackLabel, Rows.playbackMechanism, 0)
        self.gridLayout.addWidget(standardPlayback, Rows.playbackMechanism, 1)
        self.gridLayout.addWidget(simplePlayback, Rows.playbackMechanism, 2)

    @Slot()
    def playbackMechanismChanged(self, checked: bool) -> None:
        """Slot is called when a User changes the method for which audio is played back

        Args:
            checked (bool): whether the button that emitted the signal is infact checked
        """
        if checked:
            self.playbackController.playbackMechanism = self.sender().text().lower()

    def _initBufferSlider(self) -> None:
        bufferSizeLimits = (64, 4096)
        bufferSizeStepSize = 8
        initialBufferSize = self.playbackController.blockSize

        bufferSizeLabel = QLabel("Audio Buffer Block Size (bytes)")
        self.gridLayout.addWidget(bufferSizeLabel, Rows.bufferSize, 0)

        self.bufferSizeSlider = QSlider(Qt.Horizontal)
        self.bufferSizeSlider.setRange(*bufferSizeLimits)
        self.bufferSizeSlider.setSingleStep(bufferSizeStepSize)
        self.bufferSizeSlider.setTickInterval(bufferSizeStepSize)

        self.gridLayout.addWidget(self.bufferSizeSlider, Rows.bufferSize, 1)

        self.bufferSizeSpinBox = pg.SpinBox(
            bounds=bufferSizeLimits,
            step=bufferSizeStepSize,
            int=True,
            compactHeight=False,
        )

        self.gridLayout.addWidget(self.bufferSizeSpinBox, Rows.bufferSize, 2)

        self.bufferSizeSpinBox.sigValueChanging.connect(
            lambda _, y: self.bufferSizeSlider.setValue(y)
        )

        self.bufferSizeSlider.valueChanged.connect(self.bufferSizeSpinBox.setValue)
        self.bufferSizeSpinBox.sigValueChanging.connect(
            lambda _, y: self.playbackController.setBufferSize
        )

        with BlockSignals((self.bufferSizeSpinBox, self.bufferSizeSlider)):
            self.bufferSizeSpinBox.setValue(initialBufferSize)
            self.bufferSizeSlider.setValue(initialBufferSize)

    def _initTestAudioBtn(self) -> None:
        btn = QPushButton("Test Playback (simple play)", self)
        btn.clicked.connect(self.playbackController.simplePlay)
        self.gridLayout.addWidget(btn, Rows.test, 0)

    def _initSDInfoDumpBtn(self: SettingsTab) -> None:
        """Adds a button for calling ExtraSounddeviceLogging.sounddeviceDump
        to the SettingsTab object passed in. Implemented outside LoggingSettings
        class so it can be called from other SettingsTab subclasses"""
        infoDumpBtn = QPushButton("Log Audio Info", self)
        infoDumpBtn.clicked.connect(ExtraSounddeviceLogging.sounddeviceDump)
        infoDumpBtn.clicked.connect(QApplication.instance().logView.show)  # noqa: F821

        self.gridLayout.addWidget(infoDumpBtn, Rows.sdInfoDump, 0)
