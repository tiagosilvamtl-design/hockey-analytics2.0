"""Skeleton connector. Replace everything marked REPLACE."""
from __future__ import annotations

import pandas as pd

from lemieux.connectors._base import Connector, ConnectorMetadata

EXAMPLE_CONNECTOR_META = ConnectorMetadata(
    id="example",  # REPLACE
    name_en="Example Data Source",  # REPLACE
    name_fr="Exemple de source de données",  # REPLACE
    source_url="https://example.com/data",  # REPLACE
    license_note="REPLACE: describe the source's terms of use verbatim or paraphrased.",
    rate_limit_hint="REPLACE: e.g., 1 req/sec sustained.",
    key_required=False,  # REPLACE if a key is needed
    key_env_var=None,    # e.g. "EXAMPLE_API_KEY"
    safe_to_cache=True,
    tags=["example"],
)


class ExampleClient(Connector):
    meta = EXAMPLE_CONNECTOR_META

    def refresh(self, **params) -> pd.DataFrame:
        """REPLACE: fetch data and return a DataFrame matching your canonical schema.

        Use self.limiter.wait() before network calls.
        Use self.cache.get()/put() to avoid hammering the upstream source.
        """
        raise NotImplementedError("Replace this with your fetch/parse logic.")
