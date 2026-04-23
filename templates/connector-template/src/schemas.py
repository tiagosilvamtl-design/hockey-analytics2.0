"""REPLACE: pandera schemas for your connector's canonical DataFrames.

We use pandera for runtime validation so schema drift on the upstream source
surfaces loud and early. Callers can invoke `EXAMPLE_SCHEMA.validate(df)`
after `refresh()` to confirm shape before using the data.
"""
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing.pandas import Series

# REPLACE with your actual columns + types. Example below shows NHL-style stats.


class ExampleSkaterRow(pa.DataFrameModel):
    name: Series[str]
    team_id: Series[str]
    season: Series[str]
    stype: Series[int] = pa.Field(isin=[2, 3])
    sit: Series[str] = pa.Field(isin=["5v5", "5v4", "4v5", "all"])
    gp: Series[int] = pa.Field(ge=0)
    toi: Series[float] = pa.Field(ge=0)

    class Config:
        strict = False  # allow extra columns; we just assert these exist
        coerce = True
