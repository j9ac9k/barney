from __future__ import annotations

import logging
from enum import IntEnum, auto
from typing import TYPE_CHECKING

import pyqtgraph as pg
from qtpy.QtCore import Qt, Slot
from qtpy.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QSlider,
    QWidget,
)

from barney.Utilities.BlockSignals import BlockSignals

from ..QRangeSlider import RangeSlider
from .SettingsTab import SettingsTab, override

if TYPE_CHECKING:
    from typing import Any, List

    from barney.Utilities.ConfigClass import ConfigClass


logger = logging.getLogger(__name__)


class Rows(IntEnum):
    colormap_widget = auto()
    windowType = auto()
    aggregate = auto()
    range_ = auto()
    windowDuration = auto()
    preemphasis = auto()
    cutoff_f = auto()
    cursor = auto()
    actions = auto()


class SpectrogramSettings(SettingsTab):
    Rows = Rows

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        render the Spectrogram Tab
        """
        super().__init__("Spectrogram", *args, **kwargs)
        self.specController = self.plotController.specController
        self.columnThreeWidth = 80

        self.checkBoxSpaceing = 0
        self._initColorMapComboBox()
        self._initFrameDuration()
        self._initPreemphasisSilder()
        self._initFrequncyCutoff()
        self._initRangeSliders()
        self._initCursorColor()
        self.updateDisplayValues()

    @property
    def configManager(self) -> ConfigClass:
        return self.specController

    def _initCursorColor(self) -> None:
        crosshairsLabel = QLabel("Crosshairs Color")
        self.gridLayout.addLabel(crosshairsLabel, Rows.cursor)

        crossHairsColorButton = pg.ColorButton(
            color=self.specController.settings.spectrogramLineColor
        )
        crossHairsColorButton.sigColorChanging.connect(
            lambda button: self.specController.applySpectrogramLineColor(
                button.color(mode="byte")
            )
        )
        crossHairsColorButton.setFixedWidth(35)
        crossHairsColorButton.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Ignored)
        self.gridLayout.addWidget(
            crossHairsColorButton, Rows.cursor, 1, alignment=Qt.AlignHCenter
        )

    def _initFrameDuration(self) -> None:
        windowDurationLimits = (1, 150)
        windowDurationLabel = QLabel("Window Duration (ms)")
        self.gridLayout.addLabel(windowDurationLabel, Rows.windowDuration)

        self.windowDurationSlider = QSlider(Qt.Horizontal)
        self.windowDurationSlider.setRange(*windowDurationLimits)
        self.windowDurationSlider.setTickInterval(1)
        self.windowDurationSpinBox = pg.SpinBox(
            bounds=windowDurationLimits, step=1, int=True, compactHeight=False
        )
        self.windowDurationSpinBox.setFixedWidth(60)

        self.gridLayout.addWidget(self.windowDurationSlider, Rows.windowDuration, 2)

        spinboxLayout = QHBoxLayout()
        spinboxLayout.addWidget(self.windowDurationSpinBox)
        spinboxLayout.addStretch()
        self.gridLayout.addLayout(spinboxLayout, Rows.windowDuration, 3)

        self.windowDurationSpinBox.sigValueChanging.connect(
            lambda _, y: self.windowDurationSlider.setValue(int(y))
        )
        self.windowDurationSlider.valueChanged.connect(
            self.windowDurationSpinBox.setValue
        )

        self.windowDurationSpinBox.sigValueChanging.connect(
            lambda _, y: self.setWindowDuration(y)
        )

    def _initRangeSliders(self) -> None:
        # range-clipping Information
        rangeLabel = QLabel("Clip (%)", self)
        self.gridLayout.addLabel(rangeLabel, Rows.range_)

        self.rangeSlider = RangeSlider(Qt.Horizontal)
        self.rangeSlider.setMinimum(0)
        self.rangeSlider.setMaximum(100)
        self.rangeSlider.setTickPosition(QSlider.TicksBelow)

        self.rangeLowSpinBox = pg.SpinBox(
            step=1, int=True, compactHeight=False, bounds=(0, None)
        )
        self.rangeTopSpinBox = pg.SpinBox(
            step=1, int=True, compactHeight=False, bounds=(None, 100)
        )

        self.rangeTopSpinBox.sigValueChanging.connect(self._topSpinboxTriggerTopRange)
        self.rangeLowSpinBox.sigValueChanging.connect(self._lowSpinboxTriggerLowRange)
        self.rangeSlider.sliderMoved.connect(self._rangeSliderMoved)

        # set the width
        self.rangeLowSpinBox.setFixedWidth(45)
        self.rangeTopSpinBox.setFixedWidth(45)

        # add to smaller layout
        rangeTextLayout = QHBoxLayout(margin=0, spacing=0)

        rangeTextLayout.addWidget(self.rangeLowSpinBox)
        rangeTextLayout.addWidget(self.rangeTopSpinBox)
        self.gridLayout.addWidget(self.rangeSlider, Rows.range_, 2)
        self.gridLayout.addLayout(rangeTextLayout, Rows.range_, 3, Qt.AlignLeft)

    def _topSpinboxTriggerTopRange(self, _: Any, y: float) -> None:
        self.setTopRange(y)

    def _lowSpinboxTriggerLowRange(self, _: Any, y: float) -> None:
        self.setLowRange(y)

    def _rangeSliderMoved(self, _: Any) -> None:
        self.setLowRange(self.rangeSlider.low())
        self.setTopRange(self.rangeSlider.high())

    def _initColorMapComboBox(self) -> None:
        # color map information
        self.colorMapPicker = QComboBox(self)
        self.colorMapPicker.addItems(list(self.specController.colorMaps.keys()))
        self.colorMapPicker.activated["QString"].connect(self.setColorMap)
        colorMapLabel = QLabel("Color Map")
        self.gridLayout.addLabel(colorMapLabel, Rows.colormap_widget)
        self.gridLayout.addWidget(self.colorMapPicker, Rows.colormap_widget, 2)

        self.invertColors = QCheckBox("Invert")
        self.invertColors.stateChanged.connect(self.setInvertColors)
        self.invertColors.setFixedWidth(self.columnThreeWidth)
        self.gridLayout.addWidget(
            self.invertColors, Rows.colormap_widget, 3, alignment=Qt.AlignLeft
        )

    def _initPreemphasisSilder(self) -> None:
        label = QLabel("Pre-emphasis Constant", self)
        self.gridLayout.addLabel(label, Rows.preemphasis)
        self.preemphToggle = QCheckBox()
        self.preemphToggle.stateChanged.connect(self.togglePreemphasisFilter)
        self.gridLayout.addWidget(
            self.preemphToggle, Rows.preemphasis, 1, alignment=Qt.AlignHCenter
        )

        self.preEmphasisSlider = QSlider(Qt.Horizontal)
        self.preEmphasisSlider.setRange(0, 100)
        self.preEmphasisSlider.setTickInterval(1)

        self.gridLayout.addWidget(self.preEmphasisSlider, Rows.preemphasis, 2)

        self.preEmphasisSpinBox = pg.SpinBox(
            bounds=(0.0, 1.0), step=0.01, int=False, decimals=2, compactHeight=False
        )
        self.preEmphasisSpinBox.setFixedWidth(60)
        self.gridLayout.addWidget(
            self.preEmphasisSpinBox, Rows.preemphasis, 3, alignment=Qt.AlignLeft
        )

        self.preEmphasisSpinBox.sigValueChanging.connect(
            lambda _, y: self.preEmphasisSlider.setValue(int(round(y * 100)))
        )

        self.preEmphasisSlider.valueChanged.connect(
            lambda x: self.preEmphasisSpinBox.setValue(x / 100)
        )
        self.preEmphasisSpinBox.sigValueChanging.connect(
            lambda _, y: self.setPreEmphasis(y)
        )

    def _initFrequncyCutoff(self) -> None:
        # label
        label = QLabel("Frequency Cutoff (Hz)", self)
        self.gridLayout.addLabel(label, Rows.cutoff_f)
        self.freqCutOffToggle = QCheckBox()
        self.freqCutOffToggle.stateChanged.connect(self.toggleFreqCutoff)
        self.gridLayout.addWidget(
            self.freqCutOffToggle, Rows.cutoff_f, 1, alignment=Qt.AlignHCenter
        )

        self.freqCutoffSlider = QSlider(Qt.Horizontal)
        self.freqCutoffSlider.setTickInterval(1)
        self.gridLayout.addWidget(self.freqCutoffSlider, Rows.cutoff_f, 2)

        self.freqCutoffSpinBox = pg.SpinBox(step=1, int=True, compactHeight=False)
        self.freqCutoffSpinBox.setFixedWidth(60)
        self.gridLayout.addWidget(
            self.freqCutoffSpinBox, Rows.cutoff_f, 3, alignment=Qt.AlignLeft
        )

        self.freqCutoffSlider.valueChanged.connect(self.freqCutoffSpinBox.setValue)
        self.freqCutoffSpinBox.setValue(self.specController.freqCutoff)
        self.freqCutoffSpinBox.sigValueChanging.connect(
            lambda _, y: self.freqCutoffSlider.setValue(y)
        )
        self.freqCutoffSpinBox.sigValueChanging.connect(
            lambda _, y: self.setCutoffFrequency(y)
        )

    @Slot(int)
    def toggleFreqCutoff(self, enabled: int) -> None:
        self._toggleWidgets([self.freqCutoffSlider, self.freqCutoffSpinBox], enabled)
        self.specController.enableFreqCutoff = bool(enabled)

    @Slot(int)
    def togglePreemphasisFilter(self, enabled: int) -> None:
        self._toggleWidgets([self.preEmphasisSlider, self.preEmphasisSpinBox], enabled)
        self.specController.enablePreEmphasis = bool(enabled)

    def _toggleWidgets(self, widgets: List[QWidget], enable: int) -> None:
        for widget in widgets:
            widget.setEnabled(bool(enable))

    def setPreEmphasis(self, n: float) -> None:
        self.specController.preEmphasis = n

    @Slot(int)
    def setInvertColors(self, state: int) -> None:
        self.specController.invertColors = bool(state)

    @Slot(int)
    def setCutoffFrequency(self, freq: int) -> None:
        self.specController.freqCutoff = freq

    @Slot(str)
    def setColorMap(self, name: str) -> None:
        self.specController.colorMap = name

    @Slot(int)
    def setWindowDuration(self, value: int) -> None:
        self.specController.windowDuration = value / 1000

    @Slot(int)
    def setLowRange(self, value: float) -> None:
        value = int(value)
        self.rangeTopSpinBox.setMinimum(value + 1, update=False)
        self.specController.lowCap = value

    @Slot(int)
    def setTopRange(self, value: float) -> None:
        value = int(value)
        self.rangeLowSpinBox.setMaximum(value - 1, update=False)
        self.specController.highCap = value

    @override
    def updateDisplayValues(self) -> None:
        durval = int(self.specController.windowDuration * 1000)
        self.windowDurationSlider.setValue(durval)
        self.windowDurationSpinBox.setValue(durval)

        self.rangeSlider.setLow(self.specController.lowCap)
        self.rangeSlider.setHigh(self.specController.highCap)
        self.rangeTopSpinBox.setValue(self.specController.highCap)
        self.rangeLowSpinBox.setValue(self.specController.lowCap)

        with BlockSignals((self.colorMapPicker, self.invertColors)):
            self.colorMapPicker.setCurrentText(self.specController.colorMap)
            self.invertColors.setDown(self.specController.invertColors)

        self.preemphToggle.setChecked(self.specController.enablePreEmphasis)
        if self.specController.enablePreEmphasis:
            self.preEmphasisSlider.setValue(
                int(round(self.specController.preEmphasis * 100))
            )
            self.preEmphasisSpinBox.setValue(self.specController.preEmphasis)
        else:
            self.preEmphasisSlider.setValue(97)
            self.preEmphasisSpinBox.setValue(0.97)
        self.preEmphasisSlider.setEnabled(self.specController.enablePreEmphasis)
        self.preEmphasisSpinBox.setEnabled(self.specController.enablePreEmphasis)

        if self.specController.wave is not None:
            maxFreq = self.specController.wave.fs // 2
        else:
            maxFreq = 8_000

        with BlockSignals((self.freqCutoffSpinBox, self.freqCutoffSlider)):
            self.freqCutoffSlider.setRange(50, maxFreq)
            self.freqCutoffSlider.setValue(self.specController.freqCutoff)
            self.freqCutoffSlider.setEnabled(
                self.specController.settings._enableFreqCutoff
            )
            self.freqCutoffSpinBox.setMinimum(1)
            self.freqCutoffSpinBox.setMaximum(maxFreq)
            self.freqCutoffSpinBox.setValue(self.specController.freqCutoff)

        self.freqCutoffSpinBox.setEnabled(
            self.specController.settings._enableFreqCutoff
        )
        self.freqCutOffToggle.setChecked(self.specController.settings._enableFreqCutoff)
