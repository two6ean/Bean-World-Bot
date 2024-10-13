import random
import asyncio
import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.db import get_cursor, get_connection
from src.database.stock_db import load_stocks_from_db, save_stock_to_db

c = get_cursor()
conn = get_connection()

# 봇 시작 시 주식 정보를 DB에서 불러옴
stocks = load_stocks_from_db()

players = {}

#주식 명령어
# Stock 클래스 외부, 주가 업데이트 작업
@tasks.loop(minutes=30)
async def update_stock_prices():
    """주기적으로 주식 가격을 업데이트"""
    for stock in stocks:
        await stock.update_price()  # 비동기 호출이므로 await 사용
        save_stock_to_db(stock)
        if not stock.is_listed:
            for player in players.values():
                player.portfolio.pop(stock.name, None)
    print("주식 가격이 업데이트되었습니다.")

# 플레이어 클래스
class Player:
    def __init__(self, user_id):
        self.user_id = user_id
        self.coins = self.get_coins()
        self.portfolio = self.get_portfolio()

    def get_coins(self):
        """플레이어의 코인을 데이터베이스에서 가져옵니다."""
        c.execute('SELECT coins FROM user_coins WHERE user_id = ?', (self.user_id,))
        result = c.fetchone()
        if result is None:
            # 플레이어가 없으면 새로운 플레이어 생성 및 코인 설정 (초기 1000코인)
            c.execute('INSERT INTO user_coins (user_id, coins) VALUES (?, ?)', (self.user_id, 1000))
            conn.commit()
            return 1000  # 새 플레이어는 1000코인으로 시작
        return result[0]

    def update_coins(self, amount):
        """플레이어의 코인을 업데이트합니다."""
        self.coins += amount  # 기존 코인에 추가 또는 차감
        c.execute('UPDATE user_coins SET coins = ? WHERE user_id = ?', (self.coins, self.user_id))
        conn.commit()

    def get_portfolio(self):
        """플레이어의 포트폴리오를 데이터베이스에서 가져옵니다."""
        c.execute('SELECT stock_name, quantity FROM portfolio WHERE user_id = ?', (self.user_id,))
        return dict(c.fetchall())

    def update_portfolio(self, stock_name, quantity):
        """플레이어의 포트폴리오를 업데이트합니다."""
        if quantity > 0:
            # 주식 수량이 양수인 경우, 포트폴리오에 추가 또는 업데이트
            c.execute('''
            INSERT INTO portfolio (user_id, stock_name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, stock_name) DO UPDATE SET quantity = quantity + ?
            ''', (self.user_id, stock_name, quantity, quantity))
        else:
            # 주식 수량이 0 이하인 경우, 포트폴리오에서 삭제
            c.execute('DELETE FROM portfolio WHERE user_id = ? AND stock_name = ?', (self.user_id, stock_name))
        conn.commit()

    def buy_stock(self, stock, quantity: int) -> bool:
        """주식을 구매하고, 성공 시 코인을 차감하고 포트폴리오를 업데이트합니다."""
        total_cost = stock.price * quantity
        if total_cost > self.coins or not stock.is_listed:
            return False  # 코인이 부족하거나 상장폐지된 주식이면 매수 불가

        self.update_portfolio(stock.name, quantity)  # 포트폴리오 업데이트
        self.update_coins(-total_cost)  # 코인 차감
        return True

    def sell_stock(self, stock, quantity: int) -> bool:
        """주식을 판매하고, 성공 시 코인을 지급하고 포트폴리오를 업데이트합니다."""
        if stock.name not in self.portfolio or self.portfolio[stock.name] < quantity:
            return False  # 보유 주식 수량이 부족하면 매도 불가

        self.update_portfolio(stock.name, -quantity)  # 포트폴리오 업데이트 (주식 수량 감소)
        total_earnings = stock.price * quantity
        self.update_coins(total_earnings)  # 코인 지급
        return True

    def total_value(self, stocks: list) -> float:
        """보유한 주식의 총 가치를 계산"""
        value = 0
        for stock_name, quantity in self.portfolio.items():
            stock = next(s for s in stocks if s.name == stock_name)
            if stock.is_listed:
                value += stock.price * quantity
        return value
    
    # 플레이어 생성 또는 가져오기
def get_or_create_player(user_id: int) -> Player:
    """플레이어가 존재하지 않으면 생성하고, 매수/매도 후 갱신된 정보를 다시 가져옵니다."""
    if user_id not in players:
        players[user_id] = Player(user_id)
    else:
        # 매수 또는 매도 후 최신 정보로 업데이트
        players[user_id].coins = players[user_id].get_coins()  # DB에서 코인 정보를 다시 불러옴
        players[user_id].portfolio = players[user_id].get_portfolio()  # DB에서 포트폴리오 정보를 다시 불러옴
    return players[user_id]