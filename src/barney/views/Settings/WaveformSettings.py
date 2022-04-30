from __future__ import annotations

import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING

import pyqtgraph as pg
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QComboBox, QGridLayout, QGroupBox, QLabel, QSpinBox

from .SettingsTab import SettingsTab

if TYPE_CHECKING:
    from typing import Any

    from barney.Utilities.ConfigClass import ConfigClass

logger = logging.getLogger(__name__)


class Rows(IntEnum):
    audioChannelPooling = auto()
    clippingThreshold = auto()


class WaveformSettings(SettingsTab):
    Rows = Rows

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("Waveform", *args, **kwargs)
        self.waveformController = self.plotController.waveController
        self._initAudioChannelPooling()
        self._initClippingParameters()
        return None

    @property
    def configManager(self) -> ConfigClass:
        return self.waveformController

    def _initAudioChannelPooling(self) -> None:
        layout = QGridLayout()
        groupBox = QGroupBox("Multi-Channel Settings")

        channelPoolingLabel = QLabel("Waveform Multi-Channel Display:")

        poolingMethodComboBox = QComboBox(self)
        poolingMethodComboBox.addItems(list(self.waveformController.poolFuncMap.keys()))
        poolingMethodComboBox.activated["QString"].connect(self.setPoolingMethod)

        layout.addWidget(channelPoolingLabel, 1, 0)
        layout.addWidget(poolingMethodComboBox, 1, 1)
        layout.setColumnStretch(0, 100)
        groupBox.setLayout(layout)
        self.gridLayout.addWidget(groupBox, Rows.audioChannelPooling, 0, 1, -1)

    @Slot(str)
    def setPoolingMethod(self, poolingMethod: str) -> None:
        self.audioChannelPooling = poolingMethod
        self.waveformController.refreshSubplots()

    def _initClippingParameters(self) -> None:
        layout = QGridLayout()
        groupBox = QGroupBox("Clipping Parameters")

        groupBox.setCheckable(True)
        groupBox.setChecked(self.waveformController.settings.clipHighlighting)

        groupBox.clicked.connect(self.waveformController.toggleClippingRegions)
        clippingThresholdLabel = QLabel("Clipping Threshold Percentage")
        clippingThresholdSpinBox = QSpinBox()
        clippingThresholdSpinBox.setRange(0, 100)
        clippingThresholdSpinBox.setValue(
            int(self.waveformController.settings.clippingThreshold * 100)
        )
        clippingThresholdSpinBox.setSuffix("%")
        clippingThresholdSpinBox.setMinimumWidth(45)
        clippingThresholdSpinBox.valueChanged.connect(
            self.waveformController.determineClippedIndexes
        )
        layout.addWidget(clippingThresholdLabel, 1, 0)
        layout.addWidget(clippingThresholdSpinBox, 1, 1)

        clippingPadding = QLabel("Time Padding Around Clipping Points")
        clippingPaddingDurationSpinBox = QSpinBox()
        clippingPaddingDurationSpinBox.setRange(0, 100)
        clippingPaddingDurationSpinBox.setValue(
            self.waveformController.settings.clippingPaddingDuration
        )
        clippingPaddingDurationSpinBox.setSuffix(" ms")
        clippingPaddingDurationSpinBox.setMinimumWidth(55)
        clippingPaddingDurationSpinBox.setMaximumWidth(55)
        clippingPaddingDurationSpinBox.valueChanged.connect(
            self.waveformController.updateDurationPadding
        )
        layout.addWidget(clippingPadding, 2, 0)
        layout.addWidget(clippingPaddingDurationSpinBox, 2, 1)

        brushColorLabel = QLabel("Color to Highlight Clipped Region")
        brushColorButton = pg.ColorButton(
            color=self.waveformController.settings.clippingColor
        )
        brushColorButton.sigColorChanging.connect(
            lambda button: self.waveformController.updateClippingRegionColor(
                button.color(mode="byte")
            )
        )
        layout.addWidget(brushColorLabel, 3, 0)
        layout.addWidget(brushColorButton, 3, 1)

        groupBox.setLayout(layout)
        self.gridLayout.addWidget(groupBox, Rows.clippingThreshold, 0, 1, -1)
