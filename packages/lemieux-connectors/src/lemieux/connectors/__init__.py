"""Lemieux data connectors."""
from __future__ import annotations

# Inject truststore for corporate SSL-intercepted environments.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

__version__ = "0.1.0"
