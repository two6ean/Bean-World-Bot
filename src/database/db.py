import sqlite3

# SQLite 데이터베이스 설정
conn = sqlite3.connect('bot_data.db')
c = conn.cursor()

# 테이블 생성 쿼리
c.execute('''CREATE TABLE IF NOT EXISTS banned_words (word TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, name TEXT, date TEXT, end_date TEXT, location TEXT, participants TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS attendance (user_id INTEGER PRIMARY KEY, check_in_count INTEGER, last_check_in TIMESTAMP)''')
c.execute('''CREATE TABLE IF NOT EXISTS user_coins (user_id INTEGER PRIMARY KEY, coins INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS daily_tasks (user_id INTEGER PRIMARY KEY, last_reset TIMESTAMP, work_count INTEGER, problem_count INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS players (user_id INTEGER PRIMARY KEY, coins INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS stocks (name TEXT PRIMARY KEY, price REAL, previous_price REAL, is_listed BOOLEAN)''')

c.execute('''
    CREATE TABLE IF NOT EXISTS portfolio (
        user_id INTEGER,
        stock_name TEXT,
        quantity INTEGER,
        PRIMARY KEY (user_id, stock_name),
        FOREIGN KEY (user_id) REFERENCES players(user_id),
        FOREIGN KEY (stock_name) REFERENCES stocks(name)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS game_stats (
    user_id INTEGER PRIMARY KEY,
    rps_wins INTEGER DEFAULT 0,
    rps_losses INTEGER DEFAULT 0,
    rps_ties INTEGER DEFAULT 0,
    rps_net_coins INTEGER DEFAULT 0,
    odd_even_wins INTEGER DEFAULT 0,
    odd_even_losses INTEGER DEFAULT 0,
    odd_even_net_coins INTEGER DEFAULT 0,
    slot_machine_wins INTEGER DEFAULT 0,
    slot_machine_losses INTEGER DEFAULT 0,
    slot_machine_net_coins INTEGER DEFAULT 0,
    blackjack_wins INTEGER DEFAULT 0,
    blackjack_losses INTEGER DEFAULT 0,
    blackjack_ties INTEGER DEFAULT 0,
    blackjack_net_coins INTEGER DEFAULT 0,
    check_in_count INTEGER DEFAULT 0,
    work_count INTEGER DEFAULT 0,
    problem_count INTEGER DEFAULT 0
)
''')

conn.commit()

def get_cursor():
    return c

def get_connection():
    return conn