from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter_ns
from typing import TYPE_CHECKING

import pytest  # noqa: F401
from qtpy.QtCore import QModelIndex

from barney.Utilities.TimerLogger import timed_version_of

from ..helpers import openFile, rowSelector

if TYPE_CHECKING:
    from typing import List

    from pytestqt import qtbot

    from barney.views.MainWindow import MainWindow


logger = logging.getLogger(__name__)


def test_timing(viewer: MainWindow) -> None:
    controller = viewer._controller
    p = Path(__file__).parents[2] / "data" / "speech-mwm.flac"

    start_uncached = perf_counter_ns()
    controller.getTrack(p)
    stop_uncached = perf_counter_ns()
    t_uncached = stop_uncached - start_uncached

    start_cached = perf_counter_ns()
    controller.getTrack(p)
    stop_cached = perf_counter_ns()
    t_cached = stop_cached - start_cached

    assert t_cached < t_uncached, f"{t_cached} > {t_uncached}"


def precacheAll(viewer: MainWindow, qtbot: qtbot) -> List[Path]:
    paths = [
        Path(__file__).parents[2] / "data" / "speech-mwm.flac",
        Path(__file__).parents[2] / "data" / "metronome.wav",
        Path(__file__).parents[2] / "data" / "speech-mwm.wav",
    ]
    # openFile(viewer, paths, qtbot)

    for path in paths:
        assert path.exists()
        openFile(viewer, path, qtbot)
        viewer._controller.getTrack(path)  # pre-cache all
    return paths


def selectFlac(viewer: MainWindow, qtbot: qtbot) -> QModelIndex:
    # flac takes longest to load; useful for cache testing.
    viewer.lineEdit.setText("filename:speech-mwm.flac")
    viewer.lineEdit.editingFinished.emit()
    index = rowSelector(viewer, [0], qtbot)[0]
    # viewer._controller.selectIndex(index)
    return index


def test_refresh(viewer: MainWindow, qtbot: qtbot) -> None:
    controller = viewer._controller
    paths = precacheAll(viewer, qtbot)
    flac = [p for p in paths if "speech-mwm.flac" in str(p)][0]
    selectFlac(viewer, qtbot)

    getTrack = timed_version_of(controller.getTrack)
    refresh = timed_version_of(viewer.refreshAction.trigger)

    t_cached, _ = getTrack(flac)  # retrieve from cache
    t_refresh, _ = refresh()  # clear cache and get again

    assert t_refresh > t_cached, "refresh didn't work"


def isBlacklisted(viewer: MainWindow, path: Path, index: QModelIndex) -> bool:
    controller = viewer._controller
    direct = path in controller.cacheController.cacheBlacklist
    indirect = controller.cacheController.isBlacklisted(index)
    assert direct == indirect, "inconsistency in cache blacklist"
    return direct


def test_allowCaching(viewer: MainWindow, qtbot: qtbot) -> None:
    paths = precacheAll(viewer, qtbot)
    flac = [p for p in paths if "speech-mwm.flac" in str(p)][0]
    index = selectFlac(viewer, qtbot)  # gets cached here

    getTrack = timed_version_of(viewer._controller.getTrack)

    t_cached, _ = getTrack(flac)  # check cached time

    assert not isBlacklisted(viewer, flac, index)
    viewer.allowCaching(False)
    assert isBlacklisted(viewer, flac, index)

    t_blacklisted, _ = getTrack(flac)  # check unchached time

    assert t_cached < t_blacklisted, "t_cached > t_blacklisted"

    viewer.allowCaching(True)
    assert not isBlacklisted(viewer, flac, index)

    t_uncached, _ = getTrack(flac)  # should no longer be in cache
    t_cached, _ = getTrack(flac)  # now cached

    assert t_cached < t_uncached
