from datetime import date

from app.services.sm2_engine import update_sm2


def test_quality_5_increases_ease_factor_and_grows_interval_beyond_six_on_third_review():
    result = update_sm2(quality=5, ease_factor=2.5, interval=6, repetition=2)

    assert result["ease_factor"] > 2.5
    assert result["interval"] > 6
    assert result["repetition"] == 3


def test_quality_3_keeps_ease_factor_close_to_starting_value():
    result = update_sm2(quality=3, ease_factor=2.5, interval=6, repetition=2)

    assert result["ease_factor"] == 2.36
    assert abs(result["ease_factor"] - 2.5) < 0.2


def test_quality_2_resets_repetition_and_interval():
    result = update_sm2(quality=2, ease_factor=2.5, interval=6, repetition=2)

    assert result["repetition"] == 0
    assert result["interval"] == 1


def test_quality_0_full_reset():
    result = update_sm2(quality=0, ease_factor=2.5, interval=20, repetition=5)

    assert result["repetition"] == 0
    assert result["interval"] == 1
    assert result["ease_factor"] == 1.7


def test_repetition_zero_sets_interval_to_one():
    result = update_sm2(quality=4, ease_factor=2.5, interval=10, repetition=0)

    assert result["interval"] == 1
    assert result["repetition"] == 1


def test_repetition_one_sets_interval_to_six():
    result = update_sm2(quality=4, ease_factor=2.5, interval=1, repetition=1)

    assert result["interval"] == 6
    assert result["repetition"] == 2


def test_ease_factor_never_drops_below_one_point_three():
    result = update_sm2(quality=0, ease_factor=1.3, interval=3, repetition=2)

    assert result["ease_factor"] == 1.3


def test_next_review_date_is_always_today_or_later():
    result = update_sm2(quality=5, ease_factor=2.5, interval=1, repetition=0)

    assert result["next_review_date"] >= date.today()


def test_return_dict_has_all_required_keys():
    result = update_sm2(quality=5, ease_factor=2.5, interval=1, repetition=0)

    assert set(result) == {
        "ease_factor",
        "interval",
        "repetition",
        "next_review_date",
    }
