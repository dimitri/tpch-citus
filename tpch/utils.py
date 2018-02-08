def expand_step_range(steps):
    """Explode the notation 2..10 into the Python list

    [2, 3, 4, 5, 6, 7, 8, 9, 10]
    """
    try:
        step_range = steps.split('..')

        if len(step_range) == 1:
            return [int(step_range[0])]

        elif len(step_range) == 2:
            start, end = int(step_range[0]), int(step_range[1])

            return [start+x for x in range(end-start+1)]

        else:
            return []
    except Exception:
        return []
