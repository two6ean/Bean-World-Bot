import sqlite3

from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

# 사용자 코인 가져오기
def get_user_coins(user_id: int) -> int:
    c.execute("SELECT coins FROM user_coins WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

# 사용자 코인 업데이트
def update_user_coins(user_id: int, amount: int):
    c.execute("SELECT coins FROM user_coins WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row is None:
        if amount < 0:
            amount = 0
        c.execute("INSERT INTO user_coins (user_id, coins) VALUES (?, ?)", (user_id, amount))
    else:
        coins = row[0]
        new_amount = coins + amount
        if new_amount < 0:
            new_amount = 0
        c.execute("UPDATE user_coins SET coins = ? WHERE user_id = ?", (new_amount, user_id))
    conn.commit()