"""Runtime entry point helpers."""

from __future__ import annotations


def main() -> int:
    """Launch the PyQt5 desktop application."""

    from src.palletizer.gui import MainWindow, create_application

    app = create_application()
    window = MainWindow()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
