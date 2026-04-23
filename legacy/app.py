"""Streamlit entrypoint — routes to the four pages."""
from __future__ import annotations

import streamlit as st

from ui import pages_anecdata, pages_series, pages_swap, pages_team

st.set_page_config(
    page_title="claudehockey — 2026 playoffs analytics",
    page_icon="🏒",
    layout="wide",
)

PAGES = {
    "Series Overview": pages_series.render,
    "Team Dashboard": pages_team.render,
    "Swap Scenario": pages_swap.render,
    "Anecdata Comparison": pages_anecdata.render,
}


def main() -> None:
    with st.sidebar:
        st.markdown("## 🏒 claudehockey")
        st.caption("NHL 2026 playoffs — data + anecdata")
        page = st.radio("", list(PAGES.keys()), label_visibility="collapsed")
        st.markdown("---")
        st.caption(
            "Data via [Natural Stat Trick](https://www.naturalstattrick.com/) "
            "under personal-use access key. Throttled & cached."
        )
    PAGES[page]()


if __name__ == "__main__":
    main()
