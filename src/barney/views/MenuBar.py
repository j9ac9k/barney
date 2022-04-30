from __future__ import annotations

import logging
from platform import system
from typing import TYPE_CHECKING, Optional

from qtpy.QtCore import Qt, QUrl, Signal, Slot
from qtpy.QtGui import QKeySequence
from qtpy.QtWidgets import QAction, QApplication, QFileDialog, QMenu, QMenuBar

from barney.Utilities.PathMapper import qUrlToPath, qUrlToString, stringToQUrl

from ..controllers.ParseManager import ParseManager
from .Settings import SettingDialog

if TYPE_CHECKING:
    from .MainWindow import MainWindow

logger = logging.getLogger(__name__)


class MenuBar(QMenuBar):
    relayURLs = Signal(QUrl)
    relayForcedUrl = Signal(QUrl, str)
    sigUnloadAcousticModel = Signal()
    sigAcousticModelLoaded = Signal()

    def __init__(self, parent: MainWindow) -> None:
        super().__init__(parent)
        self.fileMenu = FileMenu(self)
        self.editMenu = EditMenu(self)
        self.viewMenu = ViewMenu(self)
        self.playMenu = PlayMenu(self)
        self.helpMenu = HelpMenu(self)

        for menu in [
            self.fileMenu,
            self.editMenu,
            self.viewMenu,
            self.playMenu,
            self.helpMenu,
        ]:
            self.addMenu(menu)


class HelpMenu(QMenu):
    def __init__(self, parent: MenuBar) -> None:
        super().__init__(parent)

        self.mainWindow = self.parent().parent()
        self.setTitle("Help")
        self.aboutAction()
        self.showHelpAction()

    def aboutAction(self) -> None:
        about = QAction("About", self)
        about.triggered.connect(self.mainWindow.about)
        # about.setShortcut(QKeySequence.HelpContents)
        about.setStatusTip("About Barney")
        self.addAction(about)

    def showHelpAction(self) -> None:
        helpDialog = QAction("Barney Help", self)
        helpDialog.triggered.connect(self.mainWindow.createHelpWindow)
        helpDialog.setShortcut(QKeySequence.HelpContents)
        self.addAction(helpDialog)


class PlayMenu(QMenu):
    def __init__(self, parent: MenuBar) -> None:
        super().__init__(parent)
        self.mainWindow = self.parent().parent()
        self.setTitle("Play")
        self.playAction()
        self.stopAction()

    def playAction(self) -> None:
        playpause = QAction("Play/Pause", self)
        playpause.triggered.connect(self.mainWindow.playGlobalRegion)
        playpause.setShortcut(QKeySequence(Qt.Key_Space))
        self.addAction(playpause)

    def stopAction(self) -> None:
        stop = QAction("Stop", self)
        stop.triggered.connect(self.mainWindow.sigStopRequested)
        stop.setShortcut(QKeySequence(Qt.Key_X))
        self.addAction(stop)


class ViewMenu(QMenu):
    def __init__(self, parent: MenuBar) -> None:
        super().__init__(parent)

        self.mainWindow = self.parent().parent()
        self.setTitle("View")

        self.increaseText()
        self.decreaseText()
        self.resetText()
        self.addAction(self.addSeparator())
        self.toggleLogEnergyPlot()
        self.addAction(self.addSeparator())
        self.activateConsole()
        self.addAction(self.addSeparator())
        self.viewLog()

    def increaseText(self) -> None:
        ct = QAction("IncreaseText", self)
        ct.triggered.connect(self.mainWindow.changeSize)
        ct.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_Equal))
        ct.setStatusTip("Increase text size")
        self.addAction(ct)

    def decreaseText(self) -> None:
        ct = QAction("DecreaseText", self)
        ct.triggered.connect(self.mainWindow.changeSize)
        ct.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_Minus))
        ct.setStatusTip("Decrease text size")
        self.addAction(ct)

    def resetText(self) -> None:
        ct = QAction("ResetText", self)
        ct.triggered.connect(self.mainWindow.changeSize)
        ct.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_0))
        ct.setStatusTip("Reset text size")
        self.addAction(ct)

    def activateConsole(self) -> None:
        ct = QAction("Console", self)
        ct.triggered.connect(self.mainWindow.launchConsole)
        ct.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_QuoteLeft))
        ct.setStatusTip("Launch interactive python console")
        self.addAction(ct)

    def viewLog(self) -> None:
        invokeLogAction = QAction("Show Log", self)
        invokeLogAction.setStatusTip("View log")
        invokeLogAction.triggered.connect(self.invokeLog)
        self.addAction(invokeLogAction)

    def toggleLogEnergyPlot(self) -> None:
        toggleEnergyPlotAction = QAction("Toggle Enery Plot", self)
        toggleEnergyPlotAction.setStatusTip(
            "Toggle the display of the log-energy plot in the plot area"
        )
        toggleEnergyPlotAction.triggered.connect(self.toggleLogEnergy)
        self.addAction(toggleEnergyPlotAction)

    @Slot()
    def invokeLog(self) -> None:
        QApplication.instance().logView.show()  # noqa: F821

    @Slot()
    def toggleLogEnergy(self) -> None:
        enable = not QApplication.instance().settings._showLogEnergy  # noqa
        QApplication.instance().settings._showLogEnergy = enable  # noqa
        self.mainWindow.plotView.showLogEnergyPlot(enable)
        QApplication.instance().settings.jsonDump()  # noqa
        return None


class EditMenu(QMenu):

    sigSelectFilesInDirectory = Signal()

    def __init__(self, parent: MenuBar) -> None:
        super().__init__(parent)

        self.mainWindow = self.parent().parent()
        self.setTitle("Edit")
        self.addAction(self.mainWindow.flagAction)
        self.addAction(self.mainWindow.skipAction)
        self.addAction(self.mainWindow.removeFlagAction)
        self.addAction(self.mainWindow.removeSkipAction)
        self.addAction(self.mainWindow.refreshAction)
        self.addAction(self.mainWindow.allowCachingAction)

        self.addSelectAllFilesInDirectoryAction()

    def addSelectAllFilesInDirectoryAction(self) -> None:
        selectFilesInDirectory = QAction("Select All In Same Directory", self)
        selectFilesInDirectory.setShortcut(QKeySequence(Qt.CTRL + Qt.Key_D))
        selectFilesInDirectory.setStatusTip(
            "Select all files that reside in the same directory as the currently selected file"
        )
        selectFilesInDirectory.triggered.connect(self.sigSelectFilesInDirectory)
        self.addAction(selectFilesInDirectory)


class FileMenu(QMenu):
    def __init__(self, parent: MenuBar) -> None:
        super().__init__(parent)
        self.mainWindow = self.parent().parent()
        self.globalMenu = self.parent()
        self.setTitle("File")
        self.addOpenAction()
        self.addOpenDirAction()
        self.openAs = self.addMenu("Open As...")
        self.addOpenAudioAction()
        self.addOpenDatabaseAction()
        self.addAction(self.addSeparator())
        self.addInvokeSettingAction()
        self.addAction(self.addSeparator())
        self.addExitAction()
        self.dialog: Optional[SettingDialog] = None

    def addExitAction(self) -> None:
        exitAction = QAction("&Quit", self)
        exitAction.triggered.connect(QApplication.instance().quit)  # noqa: F821
        exitAction.setShortcut(QKeySequence.Quit)
        exitAction.setStatusTip("Exit Application")
        exitAction.setMenuRole(QAction.QuitRole)
        exitAction.setPriority(QAction.HighPriority)
        self.addAction(exitAction)

    def addOpenAction(self) -> None:
        openAction = QAction("&Open", self)
        openAction.setShortcut(QKeySequence.Open)
        openAction.setStatusTip("Open File")
        openAction.triggered.connect(self.openFile)
        self.addAction(openAction)

    @Slot()
    def openFile(self) -> None:
        audio_types = ParseManager.formattedAudioFileTypes("*")
        fileUrl, selectedFilter = QFileDialog.getOpenFileUrl(
            self.mainWindow,
            "Select File to Open",
            stringToQUrl(QApplication.instance().settings._lastDirectory),  # noqa: F821
            "Database Files (*.db *.alignments *.tas *.errors);"
            + f";Audio files ({' '.join(audio_types)});"
            + ";Any File (*)",
            QApplication.instance().settings._lastFilter,  # noqa: F821
            options=QFileDialog.Options(),
        )
        if not fileUrl.isEmpty():
            QApplication.instance().settings._lastFilter = selectedFilter  # noqa: F821
            QApplication.instance().settings._lastDirectory = qUrlToPath(  # noqa: F821
                fileUrl
            ).parent.as_posix()
            QApplication.instance().settings.jsonDump()  # noqa: F821
            logger.debug(f'Passing Along "{fileUrl}"')
            self.globalMenu.relayURLs.emit(fileUrl)
        else:
            logger.debug("Canceled QFileDialog Box")

    def addOpenDirAction(self) -> None:
        openAction = QAction("Open Directory", self)
        openAction.setShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_O))
        openAction.setStatusTip("Open Directory")
        openAction.triggered.connect(self.openDir)
        self.addAction(openAction)

    def addOpenAudioAction(self) -> None:
        openAction = QAction("Audio File", self)
        openAction.setStatusTip("Open Audio File")
        openAction.triggered.connect(self.openAudio)
        self.openAs.addAction(openAction)

    def addOpenDatabaseAction(self) -> None:
        openAction = QAction("Database File", self)
        openAction.setStatusTip("Open Database")
        openAction.triggered.connect(self.openDatabase)
        self.openAs.addAction(openAction)

    @Slot()
    def openAudio(self) -> None:
        fileUrl, _ = QFileDialog.getOpenFileUrl(
            self.globalMenu,
            "Select Audio File to Open",
            stringToQUrl(QApplication.instance().settings._lastDirectory),  # noqa: F821
            "All Files (*)",
            options=QFileDialog.Options(),
        )
        if fileUrl.isEmpty():
            logger.debug("Canceled QFileDialog Box")
        else:
            logger.debug(f'Passing Along "{fileUrl}"')
            QApplication.instance().settings._lastDirectory = qUrlToPath(  # noqa: F821
                fileUrl
            ).parent.as_posix()
            QApplication.instance().settings.jsonDump()  # noqa: F821
            self.globalMenu.relayForcedUrl.emit(fileUrl, "audio")

    @Slot()
    def openDir(self) -> None:
        dirUrl = QFileDialog.getExistingDirectoryUrl(
            self.globalMenu,
            "Select Directory to Open",
            stringToQUrl(QApplication.instance().settings._lastDirectory),  # noqa: F821
            QFileDialog.Option.ShowDirsOnly,
        )
        if dirUrl != "":
            logger.debug(f'Passing Along "{dirUrl}"')
            QApplication.instance().settings._lastDirectory = qUrlToString(
                dirUrl
            )  # noqa: F821
            QApplication.instance().settings.jsonDump()  # noqa: F821
            self.globalMenu.relayURLs.emit(dirUrl)
        else:
            logger.debug("Canceled QFileDialog Box")

    @Slot()
    def openDatabase(self) -> None:
        fileUrl, _ = QFileDialog.getOpenFileUrl(
            self.globalMenu,
            "Select Database to Open",
            stringToQUrl(QApplication.instance().settings._lastDirectory),  # noqa: F821
            "All Files (*)",
            options=QFileDialog.Options(),
        )
        if fileUrl.isEmpty():
            logger.debug("Cancelled QFileDialog Box")
        else:
            logger.debug(f"Opening {fileUrl} as database file")
            QApplication.instance().settings._lastDirectory = qUrlToPath(  # noqa: F821
                fileUrl
            ).parent.as_posix()
            QApplication.instance().settings.jsonDump()  # noqa: F821
            self.globalMenu.relayForcedUrl.emit(fileUrl, "database")

    def addInvokeSettingAction(self) -> None:
        invokeSettingAction = QAction("Preferences", self)
        if system() == "Linux":
            invokeSettingAction.setShortcut(QKeySequence(Qt.Key_F10))
        invokeSettingAction.setStatusTip("Settings")
        invokeSettingAction.triggered.connect(self.invokeSetting)
        self.addAction(invokeSettingAction)

    @Slot()
    def invokeSetting(self) -> None:
        if self.dialog is None:
            self.dialog = SettingDialog(self.mainWindow)
            self.dialog.rejected.connect(self.resetSettingDialog)
            self.dialog.show()

    @Slot()
    def resetSettingDialog(self) -> None:
        self.dialog = None
