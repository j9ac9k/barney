from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from barney.Utilities.ConfigClass import ConfigClass

if TYPE_CHECKING:
    from typing import Any, Callable

    from qtpy.QtWidgets import QTabWidget

    from ...controllers.PlotController import PlotController
    from ..MainWindow import MainWindow
    from .SettingDialog import SettingDialog

logger = logging.getLogger(__name__)


def override(method: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """decorator to mark a subclass method as overriding its parent's"""
    method.overridden = True  # type: ignore
    return method


def is_overridden(method: object) -> bool:
    return hasattr(method, "overridden")


class FormGridLayout(QGridLayout):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        formLayout = QFormLayout()
        self.labelAlignment = formLayout.labelAlignment()

        self.setColumnStretch(2, 100)
        self.setVerticalSpacing(10)
        self.setHorizontalSpacing(10)
        self.setContentsMargins(5, 5, 5, 5)

    def addLabel(self, label: QLabel, row: int) -> None:
        self.addWidget(label, row, 0, alignment=self.labelAlignment)


class SettingsTab(QWidget):
    def __init__(
        self,
        name: str,
        parent: QTabWidget,
        settingsDialog: SettingDialog,
        tabEnum: int,
    ) -> None:
        super().__init__(parent)
        self.parent().insertTab(tabEnum, self, name)
        self.tabEnum = tabEnum
        self.setAccessibleName(name)
        self.settingsDialog = settingsDialog
        centralLayout = QVBoxLayout(self)
        self.gridLayout = FormGridLayout()
        centralLayout.addLayout(self.gridLayout)
        centralLayout.addStretch()
        self._initLastRow()
        self.setLayout(centralLayout)

    @property
    def mainWindow(self) -> MainWindow:
        return self.settingsDialog.mainWindow

    @property
    def plotController(self) -> PlotController:
        return self.mainWindow._controller.plotController

    def _initLastRow(self) -> None:
        box = QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, parent=self)
        box.button(QDialogButtonBox.Ok).clicked.connect(self.settingsDialog.close)

        # Reset Button
        box.addButton(QDialogButtonBox.Reset)
        box.button(QDialogButtonBox.Reset).clicked.connect(self.resetDefaults)

        # Save Settings Button
        box.addButton(QDialogButtonBox.Save)
        box.button(QDialogButtonBox.Save).clicked.connect(self.saveSettings)
        self.layout().addWidget(box)

    def plotUpdate(self) -> None:
        if self.mainWindow._model.currentWaveform is None:
            return
        self.mainWindow._controller.plotController.showWaveform.emit()

    def lastRow(self) -> int:
        """creates a last row index"""
        if not hasattr(self, "Rows"):
            return 0
        return max(self.Rows.__members__.values()) + 1

    def resetDefaults(self) -> None:
        if not hasattr(self, "configManager"):
            logger.warning(
                f"{type(self).__name__} has no config manager, and cannot reset to defaults."
            )
            return
        self.configManager.settings.resetToConfigDefaults()
        if is_overridden(self.updateDisplayValues):
            self.updateDisplayValues()
        self.configManager.refreshSubPlot()

    @staticmethod
    def saveSettings() -> None:
        ConfigClass.jsonDump()

    def updateDisplayValues(self) -> None:
        raise NotImplementedError
        # pass
