from custom_components.auckland_bin_collection.sensor import get_date_from_str
from datetime import date
from freezegun import freeze_time

@freeze_time("2023-04-02")
def test_get_date_from_str_general():
    """General passing case."""

    result = get_date_from_str("Monday 3 April")
    assert isinstance(result, date)
    assert result == date(year=2023, month=4, day=3)

@freeze_time("2023-12-30")
def test_get_date_from_str_next_year():
    """Date of next year."""

    result = get_date_from_str("Tuesday 2 January")
    assert isinstance(result, date)
    assert result == date(year=2024, month=1, day=2)

def test_get_date_from_str_invalid_input():
    """Invalid input date string."""
    
    result = get_date_from_str("INVALID DATE STRING")
    assert result is None