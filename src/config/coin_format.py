def format_coins(coins: int) -> str:
    parts = []
    if coins >= 100000000:
        parts.append(f"{coins // 100000000}억")
        coins %= 100000000
    if coins >= 10000:
        parts.append(f"{coins // 10000}만")
        coins %= 10000
    if coins > 0 or not parts:
        parts.append(f"{coins}")

    return ' '.join(parts)