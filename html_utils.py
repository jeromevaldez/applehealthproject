"""Small post-processing helpers for the Plotly HTML exports."""

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1" />'
BACK_BAR = (
    '<div class="back-bar" style="font:600 14px/1.4 -apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
    'padding:10px 16px;background:#f8f9fa;border-bottom:1px solid #e0e0e0">'
    '<a href="./" style="color:#007AFF;text-decoration:none">&larr; Apple Health</a></div>'
)


def add_viewport_meta(html_path):
    """Insert a viewport meta tag after the charset meta (kept for backwards compatibility)."""
    finalize_html(html_path)


def finalize_html(html_path, title=None, back_link=True):
    """Fix up a Plotly write_html() export for the web.

    Plotly's template has no viewport meta (phones render at 980px and shrink),
    no <title> (the tab shows the URL), and no way back to the project page.
    """
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    if 'name="viewport"' not in html:
        html = html.replace('<meta charset="utf-8" />', '<meta charset="utf-8" />' + VIEWPORT_META, 1)
    if title and "<title>" not in html:
        html = html.replace("</head>", f"<title>{title}</title></head>", 1)
    if back_link and 'class="back-bar"' not in html:
        html = html.replace("<body>\n", "<body>\n" + BACK_BAR + "\n", 1)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
