from __future__ import annotations

from typing import TYPE_CHECKING

from qtpy.QtWidgets import QApplication

from barney.views.AboutDialog import AboutDialog

if TYPE_CHECKING:
    from barney.views.MainWindow import MainWindow


def test_aboutDialog(viewer: MainWindow) -> None:
    viewer.about()
    widgs = QApplication.instance().topLevelWidgets()  # noqa: F821
    widgs = [w for w in widgs if w.isVisible()]
    assert viewer in widgs
    widgs.remove(viewer)
    assert len(widgs) == 1
    assert type(widgs[0]) is AboutDialog
    widgs[0].close()
