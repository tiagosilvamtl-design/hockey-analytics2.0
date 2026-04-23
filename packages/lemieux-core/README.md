# lemieux-core

Core analytics primitives: swap engine, isolated impact, pooled baselines, variance-aware projections.

```python
from lemieux.core import build_pooled_player_impact, project_swap, combine_swaps
```

All math is strength-state agnostic — pass 5v5 data and you get 5v5 results; pass 5v4 data and you get PP results. The engine doesn't know or care which.
