import toylib


def load_status(url):
    """Return the service status string for a URL."""
    response = toylib.get(url, 5)  # toylib 2.0 removed get()
    return response["status"]
