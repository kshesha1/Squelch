def parse_spec(s):
    """Parse a comma-separated selection string into a list of integers."""
    return [int(token.strip()) for token in s.split(",")]
