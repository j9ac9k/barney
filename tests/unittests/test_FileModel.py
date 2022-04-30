from __future__ import annotations

from typing import TYPE_CHECKING

import pytest  # noqa: F401

if TYPE_CHECKING:
    from pytestqt import qtbot, qtmodeltester
    from qtpy.QtCore import QUrl

    from barney.views.MainWindow import MainWindow


def test_fileModel(
    viewer: MainWindow,
    qtbot: qtbot,
    dbPath_relativeEntries: QUrl,
    qtmodeltester: qtmodeltester,
) -> None:
    model = viewer._model.fileProxyModel
    with qtbot.waitSignal(
        viewer._controller.fileParser.thread.success, raising=False
    ) as _:
        viewer._controller.fileParser.receiveQUrl(dbPath_relativeEntries)

    qtmodeltester.check(model)
