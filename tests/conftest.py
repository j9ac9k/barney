"""
isort:skip_file
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Generator

import pytest
import logging
from pathlib import Path

from barney.BarneyApp import Barney
from barney.Utilities.PathMapper import pathToQUrl, qUrlToPath  # noqa: F401

if TYPE_CHECKING:
    from pytestqt import qtbot
    from barney.views.MainWindow import MainWindow

logger = logging.getLogger()


@pytest.fixture(scope="session")
def app() -> Generator[Barney, None, None]:
    barney = Barney()
    yield barney
    barney.qtapp.processEvents()
    logger.removeHandler(barney.qtapp.handler)
    barney.qtapp.quit()


@pytest.fixture
def viewer(app: Barney, qtbot: qtbot) -> MainWindow:
    app.qtapp.startBarney()
    viewer = app.qtapp.mainView
    qtbot.addWidget(viewer)
    qtbot.waitExposed(viewer)
    yield viewer
    viewer.clear()
    viewer._model.fileProxyModel.setSourceModel(None)
    viewer.close()


@pytest.fixture(scope="function")
def dbPath_relativeEntries():
    dbPath = Path(__file__).parents[1] / "data" / "relative_paths.db"
    return pathToQUrl(dbPath)


@pytest.fixture(scope="function")
def wavPath():
    wavPath = Path(__file__).parents[1] / "data" / "speech-mwm.wav"
    return pathToQUrl(wavPath)


@pytest.fixture(scope="function")
def dirPath():
    dirPath = Path(__file__).parents[1]
    return pathToQUrl(dirPath)
