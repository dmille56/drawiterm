"""drawiterm package."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

try:
    __version__ = _version("drawiterm")
except PackageNotFoundError:
    # Fallback during editable/dev installs
    __version__ = "0.0.0"
