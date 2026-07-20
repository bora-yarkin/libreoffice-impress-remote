from typing import Any

# Try to import png library.
PngWriter: type[Any] | None = None

try:
    from png import Writer as _PngWriter  # type: ignore[import-not-found]

    PngWriter = _PngWriter
except ImportError:  # pragma: no cover
    pass
