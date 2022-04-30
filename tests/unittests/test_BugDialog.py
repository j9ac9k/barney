from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QApplication

from barney.BarneyApp import Barney
from barney.views.BugDialog import Bug

if TYPE_CHECKING:
    from pytestqt import qtbot

    from barney.views.MainWindow import MainWindow


def test_BugDialog(viewer: MainWindow) -> None:
    test_exc = Exception("test")
    Barney._excepthook(Exception, test_exc, None)
    widgs = QApplication.instance().topLevelWidgets()  # noqa: F821
    widgs = [w for w in widgs if w.isVisible()]
    assert viewer in widgs
    widgs.remove(viewer)
    assert len(widgs) == 1
    bug = widgs[0]
    assert type(bug) is Bug
    history = [val for _, val, _ in Bug.history]
    assert test_exc in history
    bug.close()


def test_clipboard(viewer: MainWindow, qtbot: qtbot) -> None:
    Barney._excepthook(Exception, Exception("clipboard test"), None)
    widgs = QApplication.instance().topLevelWidgets()  # noqa: F821
    widgs = [w for w in widgs if (type(w) is Bug and w.isVisible())]
    assert len(widgs) == 1
    bug = widgs[0]
    with qtbot.waitSignal(
        QApplication.instance().clipboard().dataChanged, timeout=500
    ):  # noqa: F821
        bug.copyToClipboard()
    bug.close()
