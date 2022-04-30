from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Dict, Optional, Tuple

from qtpy.QtCore import QObject, Slot

from barney.models.DataFrameInterface import DataFrameInterface

if TYPE_CHECKING:
    from qtpy.QtWidgets import QLineEdit

    from .controller import MainController

logger = logging.getLogger(__name__)


class LineEditParser(QObject):
    def __init__(self, parent: MainController) -> None:
        super().__init__(parent)
        self.mainModel = self.parent()._model

        self.fileProxyModel = self.mainModel.fileProxyModel

        self.validKeys = set(DataFrameInterface.keysOfInterest.keys())
        self.stringKeys = {
            "filename",
            "filepath",
            "speaker",
            "key",
            "orthography",
            "transcription",
            "transcriber",
        }
        self.boolKeys = {"skip", "flag", "nota"}
        self.numericalKeys = self.validKeys - self.stringKeys - self.boolKeys

        self.true_keys = {"1", "on", "yes", "y", "true", "t", "tr", "tru"}
        self.supportedOperations = {"!=", "==", ">", ">=", "=>", "<", "<=", "=<"}

    @property
    def lineEdit(self) -> QLineEdit:
        return self.parent().mainWindow.lineEdit

    def reset(self) -> None:
        """Method to run to reset filtering"""
        logger.debug("Line Edit Parser Reset Called")
        self.fileProxyModel.filterBy({})
        return None

    # TODO: should run asyncronously
    @Slot(str)
    def parse(self, textInput: str) -> None:
        print(f"Parsing {textInput}")
        logger.info(f"Received parse string {textInput}")
        self.lineEdit.setStyleSheet("")
        sortBy: Dict[str, bool] = {}
        filterBy: Dict[str, Tuple[str, float]] = {}
        regexBy: Dict[str, str] = {}

        # Operations contains <key>:<value> pairs for each entry in the qlineedit
        operations = {}
        for segment in textInput.strip().split(" "):
            key, _, value = segment.partition(":")
            if key not in self.validKeys:
                logger.warning(
                    f'Parser doesn\'t see key: "{key}" in {self.validKeys} set'
                )
                continue
            operations[key] = value
        if operations:
            logger.debug(f"Parsed commands: {operations}")
            for columnName, operation in operations.items():

                # if doing sorting
                if operation.lower() == "asc" or operation.lower() == "desc":
                    sortBy[columnName] = operation.lower() == "asc"
                # else doing filtering
                else:
                    if columnName in self.numericalKeys:
                        operatorValuePair = self._parseNumericalCriteria(operation)
                        if operatorValuePair is None:
                            logger.warning(f'Could not parse "{operation}"')
                            continue
                        filterBy[columnName] = operatorValuePair
                    elif columnName in self.boolKeys:
                        operatorValuePair = self._parseBoolCriteria(operation)
                        if operatorValuePair is None:
                            continue
                        filterBy[columnName] = operatorValuePair
                    else:
                        if not operation:
                            logger.warning("Received empty string for regex match")
                            continue
                        regexBy[columnName] = operation

        # default sort order should be by import order ascending
        if "order" not in sortBy.keys():
            sortBy["order"] = True

        # send sort ordering to the model
        self.fileProxyModel.sortBy(sortBy)
        self.fileProxyModel.filterBy(filterBy)
        try:
            self.fileProxyModel.regexBy(regexBy)
        except re.error as err:
            if err.pattern is not None:
                if isinstance(err.pattern, bytes):
                    pattern = err.pattern.decode("utf-8")
                else:
                    pattern = err.pattern

                logger.warning(f'Regex error in LineEditParser.parse:"{pattern}":{err}')
            self.lineEdit.setStyleSheet("background-color: #ff8a80;")  # red

    def _parseBoolCriteria(self, criteria: str) -> Tuple[str, int]:
        if criteria.lower() in self.true_keys:
            return "==", 1  # is True
        return "==", 0  # is False

    def _parseNumericalCriteria(self, criteria: str) -> Optional[Tuple[str, float]]:
        matchObj = re.match(
            r"(?P<operation>!?[<=>]{1,2})(?P<value>\d*(\.\d+)?)", criteria
        )
        if matchObj is None:
            logger.warning(f"Unable to numerically parse {criteria}")
            return None
        groupDict = matchObj.groupdict()

        # in case operation didn't make sense
        if groupDict["operation"] not in self.supportedOperations:
            logger.warning(
                f"Did not recognize operation {groupDict['operation']} in {criteria} expression."
            )
            return None

        # in case value didn't make sense
        if not groupDict["value"]:
            logger.warning(
                f"Did not recognize value {groupDict['value']} in {criteria} expression."
            )
            return None

        # Convert the numerical representation of a string to int or float
        value = float(groupDict["value"])
        if value.is_integer():
            value = int(value)

        return groupDict["operation"], value
