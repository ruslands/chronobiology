import pytest
import numpy as np
import pandas as pd
from chronobiology.utils import generate_data, generate_night


def test_generate_data_default():
    """Test the generate_data function with default parameters."""
    data = generate_data()

    # Ensure keys are present
    assert all(key in data for key in ["time", "value", "is_night"])

    # Ensure types are correct
    assert (
        isinstance(data["time"], np.ndarray) and data["time"].dtype == "datetime64[ns]"
    )
    assert isinstance(data["value"], np.ndarray) and data["value"].dtype == np.int64
    assert (
        isinstance(data["is_night"], np.ndarray) and data["is_night"].dtype == np.bool_
    )

    # Validate lengths
    assert len(data["time"]) == len(data["value"]) == len(data["is_night"])

    # Check if times are sorted
    assert np.all(data["time"][:-1] <= data["time"][1:])

    # Check for duplicates in time
    assert len(np.unique(data["time"])) == len(data["time"])


def test_generate_data_custom_parameters():
    """Test the generate_data function with custom parameters."""
    points_per_day = 200
    days = 5
    bg_ratio = 0.3
    data = generate_data(points_per_day=points_per_day, days=days, bg_ratio=bg_ratio)

    # Validate the total number of unique timestamps is <= points_per_day * days
    assert len(data["time"]) <= points_per_day * days

    # Validate the number of values matches the number of timestamps
    assert len(data["time"]) == len(data["value"]) == len(data["is_night"])

    # Ensure timestamps are within an extended expected range
    start_time = data["time"][0]
    end_time = data["time"][-1]
    expected_duration = np.timedelta64(days, "D")
    extended_duration = expected_duration + np.timedelta64(
        1, "h"
    )  # Allow 1-hour overlap
    assert (end_time - start_time) <= extended_duration

    # Validate background ratio
    unique_times = len(np.unique(data["time"]))
    assert unique_times >= int(points_per_day * bg_ratio * days)


def test_generate_night_default():
    """Test the generate_night function with default parameters."""
    timestamps = np.arange(
        np.datetime64("2023-01-01"), np.datetime64("2023-01-02"), np.timedelta64(5, "m")
    )
    night_flags = generate_night(timestamps)

    # Ensure the output is boolean
    assert night_flags.dtype == np.bool_

    # Validate length
    assert len(night_flags) == len(timestamps)

    # Ensure some night and day periods exist
    assert np.any(night_flags)
    assert np.any(~night_flags)


def test_generate_night_custom_period():
    """Test the generate_night function with custom night period."""
    timestamps = np.arange(
        np.datetime64("2023-01-01"),
        np.datetime64("2023-01-03"),
        np.timedelta64(10, "m"),
    )
    night_flags = generate_night(timestamps, night_period="12h")

    # Ensure alternating day-night cycles
    day_segments = timestamps[~night_flags]
    night_segments = timestamps[night_flags]

    assert len(day_segments) > 0
    assert len(night_segments) > 0
    assert np.all(day_segments[0] < night_segments[0])  # Day starts before night


if __name__ == "__main__":
    pytest.main()
