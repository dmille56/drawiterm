import runpy
import sys
from types import ModuleType


def test_main_uses_drawiterm_app(monkeypatch, tmp_path):
    # Create a fake drawiterm.app module before importing __main__
    fake_app = ModuleType("drawiterm.app")

    class FakeApp:
        def __init__(self, filepath=None):
            # Accept any value; __main__ passes Path or None
            self.filepath = filepath

        def run(self):
            # Do nothing
            return None

    fake_app.DrawitermApp = FakeApp
    monkeypatch.setitem(sys.modules, "drawiterm.app", fake_app)

    # Provide argv with a filename argument
    monkeypatch.setattr(sys, "argv", ["prog", str(tmp_path / "file.drawiterm")], raising=False)

    # Import and run the module as __main__; should not raise
    runpy.run_module("drawiterm.__main__", run_name="__main__")
