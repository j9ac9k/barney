# thank you DoTheEvo from stakcoverflow
# https://stackoverflow.com/questions/30175644/pyqt-listview-with-html-rich-text-delegate-moves-text-bit-out-of-placepic-and-c/35420113

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from qtpy.QtCore import QSize
from qtpy.QtGui import QAbstractTextDocumentLayout, QPainter, QPalette, QTextDocument
from qtpy.QtWidgets import (
    QApplication,
    QFileSystemModel,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)

if TYPE_CHECKING:
    from typing import Optional

    from qtpy.QtCore import QModelIndex
    from qtpy.QtWidgets import QWidget


class EntryDelegate(QStyledItemDelegate):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__()
        self.doc = QTextDocument(self)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        painter.save()

        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        if isinstance(index.model().sourceModel(), QFileSystemModel):
            fileSystemModel = index.model().sourceModel()
            fileSystemIndex = index.model().mapToSource(index)
            if fileSystemModel.isDir(fileSystemIndex):
                entry = defaultdict(bool)
            else:
                entry = index.model().currentSelection(index)
        else:
            entry = index.model().currentSelection(index)

        if entry is not None:
            skipText = "🤬" if entry["skip"] else " "
            flagText = "🚩" if entry["flag"] else " "
            notaText = "❓" if entry["nota"] else " "

            text = f"{notaText}{skipText}{flagText}{options.text}"
        else:
            text = f"{options.text}"
        self.doc.setHtml(text)

        options.text = ""

        style = (
            QApplication.style() if options.widget is None else options.widget.style()
        )
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()
        if option.state & QStyle.State_Selected:
            ctx.palette.setColor(
                QPalette.Text, option.palette.color(QPalette.Active, QPalette.Text)
            )

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText, options)

        if index.column() != 0:
            textRect.adjust(5, 0, 0, 0)

        thefuckyourshitup_constant = 4
        margin = (option.rect.height() - options.fontMetrics.height()) // 2
        margin = margin - thefuckyourshitup_constant
        textRect.setTop(textRect.top() + margin)

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        self.doc.documentLayout().draw(painter, ctx)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        return QSize(int(self.doc.idealWidth()), int(self.doc.size().height()))
