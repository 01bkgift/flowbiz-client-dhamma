from urllib.parse import urlparse


def redact_url(url: str) -> str:
    """
    Redacts a URL to the format: <scheme>://<domain>/***<last4chars>
    Example: https://discord.com/api/webhooks/abc123xyz -> https://discord.com/***3xyz

    If the URL is too short or invalid, attempts a best-effort redaction.
    """
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        scheme = parsed.scheme if parsed.scheme else "http"
        netloc = parsed.netloc

        # Get the full path + query to extract last 4 chars
        # We process the original string to handle cases where urlparse might be tricky with some webhook formats
        # But simpler: rely on the input string context.
        # Let's stick to the prompt spec: <scheme>://<domain>/***<last4chars>

        # Find the last 4 characters of the full input string
        full_str = url.strip()
        if len(full_str) <= 4:
            last4 = full_str
        else:
            last4 = full_str[-4:]

        return f"{scheme}://{netloc}/***{last4}"
    except Exception:
        # Fallback for completely unparseable junk, just show '***' + last 4
        if len(url) > 4:
            return f"***{url[-4:]}"
        return "***"
