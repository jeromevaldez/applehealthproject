"""Small post-processing helpers for the Plotly HTML exports."""

VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1" />'
BACK_BAR = (
    '<div class="back-bar" style="font:600 14px/1.4 -apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;'
    'padding:10px 16px;background:#f8f9fa;border-bottom:1px solid #e0e0e0">'
    '<a href="./" style="color:#007AFF;text-decoration:none">&larr; Apple Health</a></div>'
)
# The jeromevaldez.com top bar shared by every experiment. Its styles live in the
# site repo's site-bar.css, loaded from the live site so local copies show it too.
# Plotly's template keeps the browser's 8px body margin, which would inset the bar.
SITE_BAR_HEAD = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400&display=swap">'
    '<link rel="stylesheet" href="https://jeromevaldez.com/site-bar.css">'
    '<style>body{margin:0}</style>'
)
SITE_BAR = (
    '<div class="site-bar"><a href="/" class="site-bar-home" aria-label="Back to Home">'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="24" height="24" fill="currentColor" '
    'aria-hidden="true" focusable="false"><path d="M219.31,108.68l-80-80a16,16,0,0,0-22.62,0l-80,80A15.87,15.87,'
    '0,0,0,32,120v96a8,8,0,0,0,8,8h64a8,8,0,0,0,8-8V160h32v56a8,8,0,0,0,8,8h64a8,8,0,0,0,8-8V120A15.87,15.87,0,0,0,'
    '219.31,108.68ZM208,208H160V152a8,8,0,0,0-8-8H104a8,8,0,0,0-8,8v56H48V120l80-80,80,80Z"/></svg></a>'
    '<span class="site-bar-title">Apple Health Project</span></div>'
)


def add_site_bar(html):
    """Return the page with the site bar's stylesheets in <head> and the bar first in <body>."""
    if 'class="site-bar"' in html:
        return html
    html = html.replace("</head>", SITE_BAR_HEAD + "</head>", 1)
    return html.replace("<body>", "<body>\n" + SITE_BAR, 1)


def add_viewport_meta(html_path):
    """Insert a viewport meta tag after the charset meta (kept for backwards compatibility)."""
    finalize_html(html_path)


def finalize_html(html_path, title=None, back_link=True, site_bar=True):
    """Fix up a Plotly write_html() export for the web.

    Plotly's template has no viewport meta (phones render at 980px and shrink),
    no <title> (the tab shows the URL), no way back to the project page, and
    no site bar.
    """
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    if 'name="viewport"' not in html:
        html = html.replace('<meta charset="utf-8" />', '<meta charset="utf-8" />' + VIEWPORT_META, 1)
    if title and "<title>" not in html:
        html = html.replace("</head>", f"<title>{title}</title></head>", 1)
    if back_link and 'class="back-bar"' not in html:
        html = html.replace("<body>\n", "<body>\n" + BACK_BAR + "\n", 1)
    if site_bar:
        html = add_site_bar(html)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
