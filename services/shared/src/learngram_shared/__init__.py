"""learngram shared package.

Side effect on import: force stdout/stderr to UTF-8. CLI and pipeline output uses
Unicode (arrows, ellipses, middle dots), and Windows' legacy cp1252 console raises
UnicodeEncodeError on those. Every entry point imports this package, so doing it
here covers all of them. Safe to import repeatedly.
"""
import sys as _sys

for _stream in (_sys.stdout, _sys.stderr):
    try:
        if _stream is not None and (getattr(_stream, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        pass
