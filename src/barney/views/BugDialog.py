from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from types import TracebackType
    from typing import List, Optional, Tuple, Type

    from barney.views.MainWindow import MainWindow


class Bug(QDialog):

    history: List[
        Tuple[Type[BaseException], BaseException, Optional[TracebackType]]
    ] = []

    def __init__(
        self,
        parent: MainWindow,
        exc_type: Type[BaseException],
        exc_value: BaseException,
        exc_traceback: Optional[TracebackType],
    ) -> None:
        super().__init__(parent)
        import traceback

        Bug.history.append((exc_type, exc_value, exc_traceback))

        self.setWindowTitle("Bug Report")
        traceback_list = traceback.format_exception(exc_type, exc_value, exc_traceback)
        self.traceback = "".join(
            [element.rstrip() + "\n" for element in traceback_list]
        )
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        copyButton = QPushButton("Copy To Clipboard")
        copyButton.pressed.connect(self.copyToClipboard)
        self.buttonBox.addButton(copyButton, QDialogButtonBox.ApplyRole)

        mainLayout = QVBoxLayout()
        self.textEdit = QTextEdit()
        self.textEdit.setText(self.traceback.replace("\n", "\r"))
        self.textEdit.setReadOnly(True)

        mainLayout.addWidget(self.textEdit)
        mainLayout.addWidget(self.buttonBox)
        self.setFixedWidth(
            self.textEdit.width()
            + mainLayout.getContentsMargins()[0]
            + mainLayout.getContentsMargins()[2]
        )
        self.setLayout(mainLayout)

    def copyToClipboard(self) -> None:
        text = "```\r" + self.textEdit.toPlainText() + "```"
        cb = QApplication.instance().clipboard()  # noqa: F821
        cb.setText(text)
