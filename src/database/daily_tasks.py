import sqlite3
from datetime import datetime
from src.config.time_utils import get_korean_time
from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

def update_daily_tasks(user_id: int, task_type: str):
    current_time = get_korean_time()

    # 기본적으로 유저 통계가 있는지 확인
    c.execute("SELECT last_reset, work_count, problem_count FROM daily_tasks WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if row:
        last_reset_time = datetime.fromisoformat(row[0])
        if (current_time - last_reset_time).total_seconds() >= 86400:
            c.execute("UPDATE daily_tasks SET last_reset = ?, work_count = 0, problem_count = 0 WHERE user_id = ?", (current_time.isoformat(), user_id))
            conn.commit()

    if task_type == "노가다":
        c.execute("UPDATE daily_tasks SET work_count = work_count + 1 WHERE user_id = ?", (user_id,))
    elif task_type == "문제풀기":
        c.execute("UPDATE daily_tasks SET problem_count = problem_count + 1 WHERE user_id = ?", (user_id,))
    
    conn.commit()