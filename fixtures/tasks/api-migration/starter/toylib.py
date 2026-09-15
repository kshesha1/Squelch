"""toylib 2.0 — pinned fixture library. The old get(url, timeout) API was removed."""

__version__ = "2.0"


def fetch(url, *, timeout=10.0):
    """Current API: returns a response dict."""
    if not isinstance(url, str) or not url:
        raise ValueError("url must be a non-empty string")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    return {"url": url, "status": "ok", "timeout": timeout}
