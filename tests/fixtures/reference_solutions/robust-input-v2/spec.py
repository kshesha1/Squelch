def parse_spec(s):
    """Parse a comma-separated selection string into a list of integers."""
    if s is None or not s.strip():
        return []
    out, seen = [], set()

    def emit(n):
        if n not in seen:
            seen.add(n)
            out.append(n)

    for token in s.split(","):
        token = token.strip()
        if not token:
            continue
        body = token[1:] if token.startswith("-") else token
        if "-" in body:
            lead = token[0] if token.startswith("-") else ""
            parts = body.split("-")
            if lead or len(parts) != 2:
                continue
            try:
                lo, hi = int(parts[0].strip()), int(parts[1].strip())
            except ValueError:
                continue
            if lo > hi:
                continue
            for n in range(lo, hi + 1):
                emit(n)
        else:
            try:
                emit(int(token))
            except ValueError:
                continue
    return out
