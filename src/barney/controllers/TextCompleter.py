from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QCompleter

if TYPE_CHECKING:
    from ..models.CompletionModel import CompletionModel
    from .controller import MainController


# TODO: Incorporate Custom QCompleter: https://doc.qt.io/qt-5/qtwidgets-tools-customcompleter-example.html
# Reason being is the standard one will only match on the first word of the text input, and I want to
# match every word in the text input.


class TextCompleter(QCompleter):
    def __init__(self, sourceModel: CompletionModel, parent: MainController) -> None:
        super().__init__(sourceModel, parent)
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setFilterMode(Qt.MatchContains)
        # self.setCompletionMode(QCompleter.InlineCompletion)
