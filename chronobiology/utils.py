from itertools import cycle

import numpy as np
import pandas as pd


def generate_data(
    points_per_day=100,
    days=10,
    activity_period="24h",
    night_period="24h",
    bg_ratio=0.2,
    multiactivity=False,
):
    """Generate random input data.

    :type points_per_day: int
    :param points_per_day: Number of measurement points per day, defaults to ``100``.

    :type days: int
    :param days: Series length in days, defaults to ``10``.

    :type activity_period: str|int|timedelta
    :param activity_period: Activity period length, defaults to ``'24h'``.

    :type night_period: str|int|timedelta
    :param night_period: Period of night, defaults to ``'24h'``.

    :type bg_ratio: float
    :param bg_ratio: Backgraoud activity ratio, defaults to ``0.2``.

    :type multiactivity: bool
    :param multiactivity: Multiactivity, defaults to ``False``.

    :rtype: dict[str: np.array[np.datetime64]|np.array[float]|np.array[bool]]
    :return: Dictionary containing arrays ``'time'``, ``'value'`` and ``'is_night'``
        ready to be used as input for the :class:`Chronobiology` constructor.

    .. rubric:: Usage example

    ::

        >>> data = generate_data()
        >>> ca = Chronobiology(data['time'], data['value'], data['is_night'])
    """
    rng = np.random.default_rng()
    start = pd.Timestamp("2020-01-01").asm8.astype("<M8[m]")
    activity_period = pd.Timedelta(activity_period).asm8.astype("<m8[m]")
    night_period = pd.Timedelta(night_period).asm8.astype("<m8[m]")
    minute = np.timedelta64(1, "m")
    nbursts = rng.integers(1, 3, endpoint=True)
    activity_bursts = rng.integers(activity_period.astype("i8"), size=nbursts).astype("<m8[m]")

    # Generate activity
    time = np.zeros(points_per_day * days, dtype="<M8[ns]")
    value = np.ones(points_per_day * days, dtype="int")
    bg_size = int(points_per_day * bg_ratio)
    burst_size = points_per_day - bg_size
    for d in range(days):
        # Background activity
        background = start + rng.integers(activity_period.astype("i8"), size=bg_size)
        time[d * points_per_day : d * points_per_day + bg_size] = background
        # Activity bursts
        bursts = np.tile(activity_bursts, burst_size // activity_bursts.size + 1)[:burst_size]
        bursts += (60 * rng.normal(size=burst_size)).astype("<m8[m]")
        time[d * points_per_day + bg_size : (d + 1) * points_per_day] = start + bursts
        if multiactivity:
            value[d * points_per_day + bg_size : (d + 1) * points_per_day] += rng.integers(10, size=burst_size)
        d += 1
        start += activity_period
    sort = np.argsort(time)
    time = time[sort]
    value = value[sort]

    # Filter duplicate activity
    time, idx = np.unique(time, return_index=True)
    value = value[idx]

    # Generate night
    is_night = generate_night(time, night_period)

    return {"time": time, "value": value, "is_night": is_night}


def generate_night(timeseries, night_period="24h"):
    """Generate a random ``is_night`` array.

    :type timeseries: np.array[np.datetime64]
    :param timeseries: Timestamps of measurements.

    :type night_period: str|int|timedelta, optional
    :param night_period: Period of night, defualts to ``'24h'``.

    :rtype: np.array[bool]
    :return: Array denoting whether night (``True``) or day (``False``) is associated
        with a corresponding measurement.

    """
    rng = np.random.default_rng()
    night_period = pd.Timedelta(night_period).asm8.astype("<m8[m]")
    is_night = np.ones(timeseries.size, dtype="bool")
    start = timeseries[0]
    stop = timeseries[-1]
    step = pd.Timedelta("5m").asm8
    nsteps = night_period / step
    d0 = pd.Timedelta(0).asm8
    marks = []
    while d0 < night_period:
        d1 = min(d0 + rng.integers(1, 100, endpoint=True) * step, night_period)
        marks.append([d0, d1])
        d0 = d1 + rng.integers(1, 100, endpoint=True) * step
    marks = np.array(marks)
    t0 = start
    t1 = t0 + marks[0, 1]
    mark_it = cycle(np.diff(marks, axis=0, append=(marks[0] + night_period).reshape(1, -1)))
    while t0 <= stop:
        indices = np.nonzero((timeseries >= t0) & (timeseries < t1))
        is_night[indices] = False
        d0, d1 = next(mark_it)
        t0 = t0 + d0
        t1 = t1 + d1
    return is_night


if __name__ == "__main__":
    data = generate_data()
    df = pd.DataFrame(data)
    df.to_csv("data/output.csv", index=False)
