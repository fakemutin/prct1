from __future__ import annotations


def format_interval(minutes: float) -> str:
    m = int(minutes)
    if m < 60:
        return f"{m} мин"
    hours = m // 60
    rest = m % 60
    if rest == 0:
        return f"{hours} ч"
    return f"{hours} ч {rest} мин"


def parse_interval_minutes(value: str) -> float | None:
    value = value.strip().lower().replace(",", ".")
    if value.endswith("м") or value.endswith("min"):
        num = value.rstrip("min").rstrip("м").strip()
        try:
            return max(1.0, float(num))
        except ValueError:
            return None
    if value.endswith("ч") or value.endswith("h"):
        num = value.rstrip("h").rstrip("ч").strip()
        try:
            return max(1.0, float(num) * 60)
        except ValueError:
            return None
    try:
        return max(1.0, float(value))
    except ValueError:
        return None
