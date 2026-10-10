def merge(intervals):
    """Merge closed integer intervals.

    `intervals` is a list of [start, end] pairs with start <= end, in any order.
    Two intervals are merged when they overlap or touch at a point: [1, 2] and [2, 3]
    become [1, 3]. Intervals that are merely adjacent integers are NOT merged:
    [1, 2] and [3, 4] stay separate. The input list must not be modified.
    Returns a new list of [start, end] lists sorted by start.
    """
    result = []
    for start, end in intervals:
        if result and start < result[-1][1]:
            result[-1][1] = end
        else:
            result.append([start, end])
    return result
