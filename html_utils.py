"""Small post-processing helpers for the Plotly HTML exports."""

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1" />'


def add_viewport_meta(html_path):
    """Insert a viewport meta tag after the charset meta.

    Plotly's write_html() template omits it, so phones render the page at 980px
    wide and scale it down to an unreadable thumbnail.
    """
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    if 'name="viewport"' in html:
        return
    html = html.replace('<meta charset="utf-8" />', '<meta charset="utf-8" />' + VIEWPORT_META, 1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
