from typing import Hashable, Iterable, Optional

import pandas as pd

STYLES = {
    "table": {
        "border-collapse": "collapse",
        "border": "none",
        # "font-family": "arial"
    },
    "header": {
        "font-weight": "bold",
        "text-align": "center",
        "border-bottom": "1pt solid black",
    },
    "even": {},
    "odd": {"background-color": "#f5f5f5"},
    "highlight": {"background-color": "#fff59d"},
}


def style_to_str(name: str, mapper: dict[str, dict[str, str]] = STYLES) -> str:
    style = mapper[name]
    return "; ".join(f"{k}: {v}" for k, v in style.items())


def df_to_html(
    dataframe: pd.DataFrame,
    new_code_idxs: Optional[Iterable[Hashable]] = None,
):
    if new_code_idxs is None:
        new_code_idxs = []
    data = dataframe.to_dict("index")
    table_style = style_to_str("table")
    header_style = style_to_str("header")

    # header
    html = (
        f'<table style="{table_style}" cellpadding="10">'
        f'<tr style="{header_style}">'
    )
    for col in next(iter(data.values())).keys():
        html += f"<th>{col}</th>"
    html += "</tr>"

    # rows
    for i, (index, row) in enumerate(data.items()):
        if index in new_code_idxs:
            style = style_to_str("highlight")
        elif i % 2 == 0:
            style = style_to_str("even")
        else:
            style = style_to_str("odd")
        html += f'<tr style="{style}">'
        for val in row.values():
            html += f"<td>{val}</td>"
        html += "</tr>"

    html += "</tr></table>"

    return html
