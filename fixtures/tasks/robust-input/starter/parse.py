def parse_int_list(s):
    """Parse a comma-separated string of integers into a list."""
    return [int(token.strip()) for token in s.split(",")]
