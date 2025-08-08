import numpy as np
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from chronobiology.cycle import CycleAnalyzer


def test_cycle_analyzer_steps_per_day():
    ts = np.arange(
        np.datetime64("2021-01-01"),
        np.datetime64("2021-01-02"),
        np.timedelta64(1, "m"),
    )
    ca = CycleAnalyzer(ts)
    assert ca.steps_per_day == 1440
