import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.db import get_cursor, get_connection
from src.config.stock import Stock

c = get_cursor()
conn = get_connection()

# 주식 정보를 데이터베이스에서 불러오기
def load_stocks_from_db():
    stocks = []
    c.execute('SELECT name, price, previous_price, is_listed FROM stocks')
    for row in c.fetchall():
        name, price, previous_price, is_listed = row
        stock = Stock(name, price)
        stock.previous_price = previous_price
        stock.is_listed = is_listed
        stocks.append(stock)
    return stocks

pass


# 주식 정보를 데이터베이스에 저장
def save_stock_to_db(stock: Stock):
    c.execute('''
        INSERT INTO stocks (name, price, previous_price, is_listed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET price = ?, previous_price = ?, is_listed = ?
    ''', (stock.name, stock.price, stock.previous_price, stock.is_listed,
        stock.price, stock.previous_price, stock.is_listed))
    conn.commit()
    pass

# 초기 주식 목록을 DB에 저장하는 함수
def initialize_stocks_if_empty():
    c.execute('SELECT COUNT(*) FROM stocks')
    if c.fetchone()[0] == 0:  # 데이터베이스에 주식이 없으면 초기 주식을 추가
        initial_stocks = [
            Stock("제아 엔터테이먼트", 150),
            Stock("포인바게트", 100),
            Stock("빈이엇 게임즈", 900),
            Stock("아트디자인", 150),
            Stock("로즈의 타로샵", 350),
            Stock("김뜨뺌의 스팸공장", 150),
            Stock("슬비헤어", 150),
            Stock("완두콩시네마", 50)
        ]
        for stock in initial_stocks:
            save_stock_to_db(stock)
# 봇 시작 시 주식 정보를 DB에서 불러옴
stocks = load_stocks_from_db()
            # 데이터베이스가 비어 있으면 초기 주식 목록을 삽입
if not stocks:  # DB에서 불러온 주식이 없으면 초기화
    initialize_stocks_if_empty()
    stocks = load_stocks_from_db()  # 다시 불러옴