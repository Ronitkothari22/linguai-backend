from __future__ import annotations

from datetime import date, timedelta


def update_sm2(
    quality: int,
    ease_factor: float,
    interval: int,
    repetition: int,
) -> dict[str, float | int | date]:
    """Update SM-2 scheduling state for a single topic review."""
    if quality < 0 or quality > 5:
        raise ValueError("quality must be between 0 and 5")

    if quality < 3:
        new_repetition = 0
        new_interval = 1
    else:
        if repetition == 0:
            new_interval = 1
        elif repetition == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)
        new_repetition = repetition + 1

    new_ef = ease_factor + (
        0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    )
    new_ef = max(1.3, new_ef)
    next_review = date.today() + timedelta(days=new_interval)

    return {
        "ease_factor": round(new_ef, 4),
        "interval": new_interval,
        "repetition": new_repetition,
        "next_review_date": next_review,
    }
