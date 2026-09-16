import html


def sanitize(value: str) -> str:
    return html.escape(value, quote=True)
