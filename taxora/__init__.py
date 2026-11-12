"""TAXORA Python SDK — Enterprise Document & Content Taxonomy Client."""

from .client import DEFAULT_API_URL, LIVE_APP_URL, TaxoraClient, TaxoraError

__version__ = "1.0.0"

__all__ = [
    "TaxoraClient",
    "TaxoraError",
    "DEFAULT_API_URL",
    "LIVE_APP_URL",
    "__version__",
]
