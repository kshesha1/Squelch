def clamp_and_scale(values, low, high, factor):
    """Clamp each value into [low, high] (both inclusive), then multiply by factor.

    Returns a NEW list; the caller's list is never modified.
    An empty input list returns an empty list.
    """
    result = []
    for v in values:
        if v < low:
            v = low
        elif v > high:
            v = high
        result.append(v * factor)
    return result
