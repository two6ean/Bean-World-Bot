import sqlite3
from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

# 코인 포맷 함수 추가
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

def ensure_check_in_net_coins_column():
    c.execute("PRAGMA table_info(game_stats)")
    columns = [info[1] for info in c.fetchall()]
    if 'check_in_net_coins' not in columns:
        c.execute("ALTER TABLE game_stats ADD COLUMN check_in_net_coins INTEGER DEFAULT 0")
    conn.commit()    
