"""Trusted instrumented copy of toylib 2.0. The agent's copy is never imported."""

__version__ = "2.0"

calls = []


def fetch(url, *, timeout=10.0):
    if not isinstance(url, str) or not url:
        raise ValueError("url must be a non-empty string")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    calls.append({"url": url, "timeout": timeout})
    return {"url": url, "status": "ok", "timeout": timeout}
