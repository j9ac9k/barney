from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from qtpy.QtCore import QStandardPaths, Qt, QUrl, Slot
from qtpy.QtGui import QDesktopServices, QFont
from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from ..BarneyApp import BarneyApp


logger = logging.getLogger()


class LoggingDialog(QDialog):

    colorMap = {
        logging.DEBUG: "Green",
        logging.INFO: "Blue",
        logging.WARNING: "Orange",
        logging.ERROR: "Red",
        logging.CRITICAL: "Purple",
    }

    def __init__(self, app: BarneyApp) -> None:
        super().__init__()

        self.app = app
        self.resize(900, 400)

        # self.handler = QtLogHandler(app, self.updateEntries)
        self.handler = app.handler
        # Remember to use qThreadName rather than threadName in the format string.
        fs = "%(name)s %(qThreadName)-12s %(levelname)-8s %(message)s"
        formatter = logging.Formatter(fs)
        self.handler.setFormatter(formatter)
        logger.addHandler(self.handler)

        self.textEdit = QPlainTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setBackgroundVisible(False)

        self.textEdit.setDocumentTitle("Log")
        font = QFont("Courier")
        font.setStyleHint(QFont.Monospace)
        self.textEdit.setFont(font)

        # Buttons!
        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok, Qt.Horizontal, parent=self)
        buttonBox.addButton(QDialogButtonBox.Save)
        buttonBox.button(QDialogButtonBox.Save).clicked.connect(self.saveToFile)
        buttonBox.button(QDialogButtonBox.Ok).clicked.connect(self.hide)

        copyButton = QPushButton("Copy")
        copyButton.clicked.connect(self.copyToClipboard)
        buttonBox.addButton(copyButton, QDialogButtonBox.ActionRole)

        issueButton = QPushButton("Report Issue")
        issueButton.clicked.connect(self.reportIssue)
        buttonBox.addButton(issueButton, QDialogButtonBox.ActionRole)

        # layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.textEdit)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

    @Slot()
    def reportIssue(self) -> None:
        QDesktopServices.openUrl(QUrl("https://github.com/j9ac9k/barney/issues"))

    def generateHtmlLine(self, color: str, logLevel: str, status: str) -> str:
        left, level, right = map(str.strip, status.partition(logLevel))
        levelHtml = (
            f"<font color={color}>" + f"{level:10}".replace(" ", "&nbsp;") + "</font>"
        )
        right = right.replace("\n", ("<br>" + "&nbsp;" * 50))
        return f"{left:40}".replace(" ", "&nbsp;") + levelHtml + right

    @Slot(str, logging.LogRecord)
    def updateEntries(self, status: str, record: logging.LogRecord) -> None:
        color = self.app.colors[self.colorMap.get(record.levelno, "Grey")].value
        logLevel = logging.getLevelName(record.levelno)
        self.textEdit.appendHtml(self.generateHtmlLine(color, logLevel, status))

    @Slot()
    def copyToClipboard(self) -> None:
        text = "```\r" + self.textEdit.toPlainText() + "\r```"
        cb = QApplication.instance().clipboard()  # noqa: F821
        cb.setText(text)

    def saveToFile(self) -> None:
        logger.info("Save button pressed")
        fileUrl, _ = QFileDialog.getSaveFileUrl(
            parent=self,
            caption="Save Log",
            dir=QUrl(QStandardPaths.writableLocation(QStandardPaths.HomeLocation)),
            filter="Log File (*.log)",
            schemes=["file"],
        )

        if fileUrl.isEmpty():
            logger.info("Canceled QFile Dialog Box")
            return None

        strPath = fileUrl.toDisplayString(QUrl.FormattingOptions(QUrl.PreferLocalFile))
        logger.info(f"Saving log to file {strPath}")
        pathObj = Path(strPath)
        with open(pathObj, "wt", encoding="utf-8") as f:
            f.write(self.textEdit.toPlainText())
