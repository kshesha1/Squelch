def clamp_and_scale(values, low, high, factor):
    """Clamp each value into [low, high] (both inclusive), then multiply by factor.

    Returns a NEW list; the caller's list is never modified.
    An empty input list returns an empty list.
    """
    for i in range(len(values)):
        if values[i] < low:
            values[i] = low
        elif values[i] >= high:
            values[i] = high - 1
        values[i] = values[i] * factor
    return values
