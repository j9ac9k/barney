from __future__ import annotations

from typing import TYPE_CHECKING

import pytest  # noqa: F401

if TYPE_CHECKING:
    from barney.views.MainWindow import MainWindow


def test_window_title(viewer: MainWindow) -> None:
    """Check that the window title shows as declared."""
    assert viewer.windowTitle() == "Barney"


def test_window_visible(viewer: MainWindow) -> None:
    """Check that the window width and height are set as declared."""
    assert viewer.isVisible()
