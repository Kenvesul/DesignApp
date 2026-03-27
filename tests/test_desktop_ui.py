import pytest

pytest.importorskip("PySide6")
pytest.importorskip("matplotlib")

from PySide6.QtWidgets import QApplication

from desktop.main_window import MainWindow


def test_main_window_has_expected_tabs():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert labels == ["Dashboard", "Slope", "Foundation", "Wall", "Pile", "Sheet Pile"]


def test_dark_mode_action_is_checkable():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)
    assert window.theme_action.isCheckable()


def test_dashboard_updates_analysis_card():
    app = QApplication.instance() or QApplication([])
    window = MainWindow(app)
    window.dashboard_page.update_analysis(
        "Wall",
        {"status": "PASS", "summary": "Ka=0.333, C2 slide=1.81", "passes": True},
    )
    assert window.dashboard_page.cards["Wall"]["status"].text() == "PASS"
    assert "Ka=0.333" in window.dashboard_page.cards["Wall"]["summary"].text()
