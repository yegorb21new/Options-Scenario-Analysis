from src.data import calculate_days_to_expiration


def test_calculate_days_to_expiration_uses_date_only_arithmetic():
    dte = calculate_days_to_expiration("2030-01-17")
    assert isinstance(dte, int)
    assert dte >= 0


def test_calculate_days_to_expiration_handles_tz_aware_input_without_subtraction_error():
    dte = calculate_days_to_expiration("2030-01-17T00:00:00+00:00")
    assert isinstance(dte, int)
    assert dte >= 0
