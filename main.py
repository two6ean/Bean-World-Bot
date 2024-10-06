import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
from dotenv import load_dotenv
import re
import os
import pytz
from datetime import datetime, timedelta
import discord.utils
import random
import asyncio
import json
import requests
import psutil
import yt_dlp as youtube_dl
import nacl
import sys

from src.config.config import TOKEN, ANNOUNCEMENT_CHANNEL_ID, ADMIN_ROLE_ID, USER_IDS, KST
from src.database.db import get_cursor, get_connection
from src.config.ytdl import ytdl_format_options, ffmpeg_options
from src.config.hangang_api import Hangang
from src.database.coin_management import get_user_coins, update_user_coins
from src.database.game_stats import update_rps_stats, update_odd_even_stats, update_slot_machine_stats, update_blackjack_stats
from src.database.daily_tasks import update_daily_tasks
from src.config.coin_setup import format_coins, ensure_check_in_net_coins_column
from src.config.time_utils import get_korean_time
from src.command.hangang import hangang
from src.command.sponsor import sponsor
from src.command.ping import ping
from src.command.announcement import announcement
from src.command.banned_word import banned_word
from src.command.timeout import timeout
from src.command.ban import ban
from src.event.messge import handle_message
from src.command.event import event
from src.command.attendance_check import attendance_check
from src.command.attendance_raking import attendance_ranking
from src.command.delete import delete
from src.command.blackjack_help import blackjack_help
from src.command.blackjack import blackjack
from src.command.help_slot import help_slot
from src.command.odd_even import odd_even
from src.command.update import update

c = get_cursor()
conn = get_connection()

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

youtube_dl.utils.bug_reports_message = lambda: ''

# 메시지 검사 및 타임아웃 처리
@bot.event
async def on_message(message):    
    await handle_message(message, bot, c)
    await bot.process_commands(message)

@bot.tree.command(name="코인관리", description="사용자에게 코인을 지급하거나 차감합니다.")
@app_commands.choices(옵션=[
    app_commands.Choice(name="지급", value="지급"),
    app_commands.Choice(name="차감", value="차감")
])
@app_commands.describe(옵션="지급 또는 차감을 선택하세요.", 사용자="대상 사용자", 금액="금액을 입력하세요.")
@app_commands.guild_only()
async def manage_coins(interaction: discord.Interaction, 옵션: app_commands.Choice[str], 사용자: discord.Member, 금액: int):
    try:
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        if 금액 <= 0:
            await interaction.response.send_message("금액은 0보다 커야 합니다.", ephemeral=True)
            return

        user_id = 사용자.id
        current_coins = get_user_coins(user_id)

        if 옵션.value == "지급":
            new_coins = current_coins + 금액
            action = "지급"
        else:
            if 금액 > current_coins:
                await interaction.response.send_message("사용자의 코인이 부족합니다.", ephemeral=True)
                return
            new_coins = current_coins - 금액
            action = "차감"

        if current_coins == 0 and 옵션.value == "차감":
            await interaction.response.send_message("사용자의 코인이 부족합니다.", ephemeral=True)
            return
        
        update_user_coins(user_id, 금액 if 옵션.value == "지급" else -금액)

        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"코인 {action} 완료",
                description=(
                    f"{사용자.mention}님에게 {format_coins(금액)}개 🪙 코인을 {action}했습니다.\n"
                    f"현재 {사용자.display_name}의 코인: {format_coins(new_coins)}개 🪙"
                ),
                color=discord.Color.green()
            ),
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)
        
class MoneyMakingView(discord.ui.View):
    def __init__(self, user_id, button_states=None, page=0, buttons_clicked=0):
        super().__init__(timeout=300)  # 5분 타임아웃 설정
        self.user_id = user_id
        self.page = page
        self.buttons_clicked = buttons_clicked
        self.button_states = button_states if button_states else [False] * 20
        self.buttons = []

        start = page * 10
        end = start + 10
        for i in range(start, end):
            button = discord.ui.Button(label="⬜", custom_id=f"work_{i+1}", style=discord.ButtonStyle.success if self.button_states[i] else discord.ButtonStyle.primary)
            button.callback = self.on_button_click
            button.disabled = self.button_states[i]
            self.add_item(button)
            self.buttons.append(button)

        if page > 0:
            prev_button = discord.ui.Button(label="이전", style=discord.ButtonStyle.secondary)
            prev_button.callback = self.prev_page
            self.add_item(prev_button)

        if end < 20:
            next_button = discord.ui.Button(label="다음", style=discord.ButtonStyle.secondary)
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def on_button_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 작업은 당신이 시작한 작업이 아닙니다.", ephemeral=True)
            return

        self.buttons_clicked += 1
        button_index = int(interaction.data['custom_id'].split('_')[1]) - 1
        self.button_states[button_index] = True
        button = discord.utils.get(self.buttons, custom_id=interaction.data['custom_id'])
        button.style = discord.ButtonStyle.success
        button.disabled = True
        await interaction.response.edit_message(view=self)

        if self.buttons_clicked == 20:
            update_user_coins(self.user_id, 20)
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="노가다 완료!",
                    description=f"20개의 버튼을 모두 클릭하여 20개의 코인을 획득했습니다! 현재 코인: {format_coins(get_user_coins(self.user_id))}개 🪙",
                    color=discord.Color.green()
                )
            )
            update_daily_tasks(self.user_id, "노가다")
            bot.ongoing_tasks.remove(self.user_id)
            self.stop()
        else:
            embed = discord.Embed(
                title="노가다 작업",
                description=f"{self.buttons_clicked}/20 버튼을 클릭했습니다.",
                color=discord.Color.blue()
            )
            await interaction.edit_original_response(embed=embed, view=self)

    async def prev_page(self, interaction: discord.Interaction):
        self.page -= 1
        await interaction.response.edit_message(view=MoneyMakingView(self.user_id, self.button_states, self.page, self.buttons_clicked))

    async def next_page(self, interaction: discord.Interaction):
        self.page += 1
        await interaction.response.edit_message(view=MoneyMakingView(self.user_id, self.button_states, self.page, self.buttons_clicked))


class ArithmeticProblemView(discord.ui.View):
    def __init__(self, user_id, correct_answer):
        super().__init__(timeout=300)  # 5분 타임아웃 설정
        self.user_id = user_id
        self.correct_answer = correct_answer

        choices = [correct_answer, correct_answer + random.randint(1, 10), correct_answer - random.randint(1, 10), correct_answer + random.randint(11, 20)]
        random.shuffle(choices)

        for choice in choices:
            button = discord.ui.Button(label=str(choice), custom_id=str(choice))
            button.callback = self.on_button_click
            self.add_item(button)

    async def on_button_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 작업은 당신이 시작한 작업이 아닙니다.", ephemeral=True)
            return

        selected_answer = int(interaction.data['custom_id'])
        if selected_answer == self.correct_answer:
            update_user_coins(self.user_id, 10)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="정답입니다!",
                    description=f"10개의 코인을 획득했습니다! 현재 코인: {format_coins(get_user_coins(self.user_id))}개 🪙",
                    color=discord.Color.green()
                )
            )
            update_daily_tasks(self.user_id, "문제풀기")
            bot.ongoing_tasks.remove(self.user_id)
            self.stop()
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="오답입니다!",
                    description="다시 시도하세요!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

    async def on_timeout(self):
        await self.message.edit(
            embed=discord.Embed(
                title="시간 초과",
                description="시간이 초과되었습니다. 다시 시도해주세요.",
                color=discord.Color.red()
            ),
            view=None
        )
        bot.ongoing_tasks.remove(self.user_id)

bot.ongoing_tasks = set()

def check_and_reset_daily_tasks(user_id):
    current_time = get_korean_time()
    reset = False

    c.execute("SELECT last_reset, work_count, problem_count FROM daily_tasks WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if row:
        last_reset, work_count, problem_count = row
        last_reset_time = datetime.fromisoformat(last_reset).astimezone(KST)
        if (current_time - last_reset_time).total_seconds() >= 86400: 
            reset = True
            work_count = 0
            problem_count = 0
            c.execute("UPDATE daily_tasks SET last_reset = ?, work_count = ?, problem_count = ? WHERE user_id = ?", (current_time.isoformat(), work_count, problem_count, user_id))
            conn.commit()
    else:
        reset = True
        work_count = 0
        problem_count = 0
        c.execute("INSERT INTO daily_tasks (user_id, last_reset, work_count, problem_count) VALUES (?, ?, ?, ?)", (user_id, current_time.isoformat(), work_count, problem_count))
        conn.commit()

    return reset, work_count, problem_count, current_time

@bot.tree.command(name="돈벌기", description="노가다 또는 문제풀기를 선택하여 돈을 법니다.")
@app_commands.choices(option=[
    app_commands.Choice(name="노가다", value="노가다"),
    app_commands.Choice(name="문제풀기", value="문제풀기")
])
@app_commands.guild_only()
async def money_making_command(interaction: discord.Interaction, option: app_commands.Choice[str]):
    try:
        user_id = interaction.user.id
        reset, work_count, problem_count, last_reset_time = check_and_reset_daily_tasks(user_id)
        current_time = get_korean_time()

        if option.value == "노가다":
            if work_count >= 5:
                time_diff = (current_time - last_reset_time).total_seconds()
                time_remaining = 86400 - time_diff
                hours, remainder = divmod(time_remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="노가다 제한",
                        description=f"오늘은 더 이상 노가다 작업을 할 수 없습니다. 내일 다시 시도하세요. 남은 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            if user_id in bot.ongoing_tasks:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="진행 중인 작업",
                        description="이미 진행 중인 노가다 작업이 있습니다.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            embed = discord.Embed(
                title="노가다 작업",
                description="20개의 버튼을 클릭하여 20개의 코인을 획득하세요!",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            message = await interaction.original_response()
            view = MoneyMakingView(user_id)
            await message.edit(view=view)
            bot.ongoing_tasks.add(user_id)
        elif option.value == "문제풀기":
            if problem_count >= 5:
                time_diff = (current_time - last_reset_time).total_seconds()
                time_remaining = 86400 - time_diff
                hours, remainder = divmod(time_remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="문제풀기 제한",
                        description=f"오늘은 더 이상 문제풀기를 할 수 없습니다. 내일 다시 시도하세요. 남은 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            if user_id in bot.ongoing_tasks:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="진행 중인 작업",
                        description="이미 진행 중인 문제풀기 작업이 있습니다.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            num1 = random.randint(1, 50)
            num2 = random.randint(1, 50)
            operator = random.choice(['+', '-', '*', '/'])
            if operator == '+':
                correct_answer = num1 + num2
            elif operator == '-':
                correct_answer = num1 - num2
            elif operator == '*':
                correct_answer = num1 * num2
            else:
                num1 = num1 * num2
                correct_answer = num1 // num2

            problem_text = f"{num1} {operator} {num2} = ?"
            view = ArithmeticProblemView(user_id, correct_answer)
            embed = discord.Embed(
                title="문제풀기",
                description=f"다음 문제를 풀어주세요: `{problem_text}`",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, view=view)
            bot.ongoing_tasks.add(user_id)
        else:
            await interaction.response.send_message("올바르지 않은 옵션입니다.", ephemeral=True)
    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)
        else:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

# 내코인 명령어
@bot.tree.command(name="내코인", description="내가 가진 코인 수를 확인합니다.")
@app_commands.guild_only()
async def my_coins_command(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        coins = get_user_coins(user_id)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="💰 내 코인",
                description=f"현재 코인: {format_coins(coins)}개 🪙",  # format_coins() 함수로 통일
                color=discord.Color.blue()
            )
        )
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

@bot.tree.command(name="코인랭킹", description="코인 랭킹을 표시합니다.")
@app_commands.guild_only()
async def coin_ranking_command(interaction: discord.Interaction):
    try:
        c.execute("SELECT user_id, coins FROM user_coins ORDER BY coins DESC LIMIT 10")
        rankings = c.fetchall()

        if rankings:
            embed = discord.Embed(title="🏆 코인 랭킹", color=discord.Color.gold())
            ranking_text = ""
            rank_emojis = ["🥇", "🥈", "🥉"] + [f"🏅{i+4}" for i in range(7)]
            for i, (user_id, coins) in enumerate(rankings):
                user = await bot.fetch_user(user_id)
                ranking_text += f"{rank_emojis[i]} **{user.name}**: {format_coins(coins)}개 🪙\n"
            embed.add_field(name="TOP 10", value=ranking_text, inline=False)
        else:
            embed = discord.Embed(title="🏆 코인 랭킹", description="코인 기록이 없습니다.", color=discord.Color.gold())

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

@bot.tree.command(name="가위바위보", description="가위바위보 게임을 합니다.")
@app_commands.describe(배팅="배팅할 코인 수", 선택="가위, 바위, 보 중 하나를 선택하세요")
@app_commands.choices(선택=[
    app_commands.Choice(name="가위", value="가위"),
    app_commands.Choice(name="바위", value="바위"),
    app_commands.Choice(name="보", value="보")
])
@app_commands.guild_only()
async def rps_command(interaction: discord.Interaction, 배팅: int, 선택: app_commands.Choice[str]):
    try:
        user_id = interaction.user.id
        current_coins = get_user_coins(user_id)
        if 배팅 > current_coins:
            await interaction.response.send_message("배팅할 코인이 부족합니다.", ephemeral=True)
            return

        user_choice = 선택.value
        bot_choice = random.choice(["가위", "바위", "보"])
        result = ""
        net_coins = 0  # net_coins 변수를 초기화합니다.

        # 배팅 금액을 먼저 차감합니다.
        update_user_coins(user_id, -배팅)

        if user_choice == bot_choice:
            result = "무승부"
            net_coins = 배팅  # 무승부 시 배팅 금액 반환
            update_user_coins(user_id, 배팅)  # 반환 처리
        elif (user_choice == "가위" and bot_choice == "보") or \
            (user_choice == "바위" and bot_choice == "가위") or \
            (user_choice == "보" and bot_choice == "바위"):
            result = "승리"
            net_coins = int(배팅 * 1.5)  # 승리 시 배팅 금액의 50% 추가
            update_user_coins(user_id, net_coins)
        else:
            result = "패배"
            net_coins = 0  # 패배 시 net_coins는 이미 차감되었으므로 0

        update_rps_stats(user_id, result, 배팅)

        color = discord.Color.green() if result == "승리" else discord.Color.red() if result == "패배" else discord.Color.orange()
        embed = discord.Embed(
            title="가위바위보 결과",
            description=(
                f"**{interaction.user.mention}님의 선택:** {user_choice}\n"
                f"**봇의 선택:** {bot_choice}\n"
                f"**결과:** {result}\n"
                f"**변동 코인:** {net_coins - 배팅 if result == '승리' else net_coins} 🪙\n"
                f"**현재 코인:** {get_user_coins(user_id)} 🪙"
            ),
            color=color
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

#주식 명령어
class Stock:
    def __init__(self, name, price):
        self.name = name
        self.price = price
        self.previous_price = price
        self.is_listed = True

    async def update_price(self):
        """주식 가격을 무작위로 변동 및 상장폐지 조건 추가"""
        if not self.is_listed:
            return

        self.previous_price = self.price
        self.price *= random.uniform(0.9, 1.1)
        self.price = round(self.price)

        if self.price < 5:
            await self.delist()  # 비동기 메서드이므로 await 추가

        save_stock_to_db(self)

    async def delist(self):
        """주식을 상장폐지 상태로 변경"""
        self.is_listed = False
        print(f"{self.name} 주식이 상장폐지되었습니다.")
        # 주식 상장 폐지 후 재상장을 비동기적으로 예약
        await self.schedule_relist()

    async def schedule_relist(self):
        """상장 폐지된 주식을 일정 시간 후에 다시 상장"""
        print(f"{self.name} 주식이 1시간 후에 다시 상장됩니다.")
        await asyncio.sleep(3600)  # 테스트용으로 10초 대기 (실제 환경에서는 3600초로 변경)
        await self.relist()

    async def relist(self):
        """주식을 다시 상장 처리"""
        self.is_listed = True
        self.price = max(10, round(self.previous_price * random.uniform(0.9, 1.1)))  # 최소 가격 10으로 설정
        self.previous_price = self.price
        save_stock_to_db(self)
        print(f"{self.name} 주식이 다시 상장되었습니다!")
        await self.update_price()  # 상장 후 가격 변동
    
    def price_change(self):
        """현재 주식 가격과 이전 가격의 차이를 계산"""
        return self.price - self.previous_price
    
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

# 주식 정보를 데이터베이스에 저장
def save_stock_to_db(stock: Stock):
    c.execute('''
        INSERT INTO stocks (name, price, previous_price, is_listed)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET price = ?, previous_price = ?, is_listed = ?
    ''', (stock.name, stock.price, stock.previous_price, stock.is_listed,
        stock.price, stock.previous_price, stock.is_listed))
    conn.commit()

# 초기 주식 목록을 DB에 저장하는 함수
def initialize_stocks_if_empty():
    c.execute('SELECT COUNT(*) FROM stocks')
    if c.fetchone()[0] == 0:  # 데이터베이스에 주식이 없으면 초기 주식을 추가
        initial_stocks = [
            Stock("제아 엔터테이먼트", 150),
            Stock("포인바게트", 100),
            Stock("빈이엇 게임즈", 900),
            Stock("바보헬스", 150),
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

players = {}

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

@bot.tree.command(name="주식목록", description="현재 주식 가격을 확인합니다.")
async def show_stocks(interaction: discord.Interaction):
    stock_message = "```diff\n"

    for stock in stocks:
        if stock.is_listed:
            change = stock.price_change()  # 주식의 가격 변동량 계산

            if change > 0:
                status = f"+ {stock.name}: 💰{int(stock.price)} ( ▲ {int(change)} )\n"
            elif change < 0:
                status = f"- {stock.name}: 💰{int(stock.price)} ( ▼ {abs(int(change))} )\n"
            else:
                status = f"  {stock.name}: 💰{int(stock.price)} ( ■ {int(change)} )\n"
        else:
            status = f"  {stock.name}: 💰{int(stock.price)} ( 상장폐지 )\n"

        stock_message += status

    stock_message += "```"

    embed = discord.Embed(title="📈 주식 목록", description=stock_message, color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)
# 매수 명령어
@bot.tree.command(name="매수", description="주식을 매수합니다.")
@app_commands.describe(stock_name="구매할 주식 이름", quantity="구매할 수량")
async def buy_stock(interaction: discord.Interaction, stock_name: str, quantity: int):
    user_id = interaction.user.id
    player = get_or_create_player(user_id)
    coins = get_user_coins(user_id)
    stock = next((s for s in stocks if s.name.lower() == stock_name.lower()), None)
    
    if not stock or not stock.is_listed:
        await interaction.response.send_message(f"{stock_name} 주식은 존재하지 않거나 상장폐지 상태입니다.", ephemeral=True)
        return

    if player.buy_stock(stock, quantity):
        # 매수 후 코인 업데이트
        coins = player.get_coins()  # 매수 후 최신 코인 상태 가져오기
        await interaction.response.send_message(f"{interaction.user.mention}님, {stock.name} 주식 {quantity}주를 성공적으로 구매했습니다. 현재 코인: {format_coins(coins)}개 🪙", ephemeral=True)
    else:
        await interaction.response.send_message(f"{interaction.user.mention}님, 코인이 부족하거나 구매할 수 없는 주식입니다.", ephemeral=True)

# 매도 명령어
@bot.tree.command(name="매도", description="주식을 매도합니다.")
@app_commands.describe(stock_name="판매할 주식 이름", quantity="판매할 수량")
async def sell_stock(interaction: discord.Interaction, stock_name: str, quantity: int):
    user_id = interaction.user.id
    player = get_or_create_player(user_id)
    coins = get_user_coins(user_id)
    stock = next((s for s in stocks if s.name.lower() == stock_name.lower()), None)
    
    if not stock or not stock.is_listed:
        await interaction.response.send_message(f"{stock_name} 주식은 존재하지 않거나 상장폐지 상태입니다.", ephemeral=True)
        return

    if player.sell_stock(stock, quantity):
        # 매도 후 코인 업데이트
        coins = player.get_coins()  # 매도 후 최신 코인 상태 가져오기
        await interaction.response.send_message(f"{interaction.user.mention}님, {stock.name} 주식 {quantity}주를 성공적으로 판매했습니다. 현재 코인: {format_coins(coins)}개 🪙", ephemeral=True)
    else:
        await interaction.response.send_message(f"{interaction.user.mention}님, 보유한 주식 수량이 부족합니다.", ephemeral=True)

# 자산 조회 명령어
@bot.tree.command(name="자산", description="플레이어의 자산을 확인합니다.")
async def show_portfolio(interaction: discord.Interaction):
    user_id = interaction.user.id
    player = get_or_create_player(user_id)
    coins = get_user_coins(user_id)
    total_value = player.total_value(stocks) + coins
    portfolio_str = '\n'.join([f"{stock_name}: {quantity}주" for stock_name, quantity in player.portfolio.items()]) or "보유 주식 없음"
    
    embed = discord.Embed(
        title=f"💼 {interaction.user.display_name}님의 자산",
        color=discord.Color.green()
    )
    embed.add_field(name="보유 주식", value=portfolio_str, inline=False)
    embed.add_field(name="현재 코인", value=f"{format_coins(coins)}개 🪙", inline=False)  # format_coins() 함수로 통일
    embed.add_field(name="총 자산", value=f"{format_coins(total_value)}개 🪙", inline=False)  # format_coins() 함수로 통일
    
    await interaction.response.send_message(embed=embed)

# 도움말 명령어
class DonateView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="🔍도움말", url="https://happy-burn-b3c.notion.site/Bean-World-Bot-Wiki-9510929dacea47688691cfe3cbae8afe"))

@bot.tree.command(name="도움말", description="명령어 사용을 도와줍니다.")
@app_commands.guild_only()
async def donate_command(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="도움말",
            description=(
                "Bean World Bot 명령어를 몰라서 불편함을 느끼셨나요?\n"
                "그래서 준비했습니다! 도! 움! 말!\n\n"
                "**사용방법**\n\n"
                "아래의 버튼을 클릭해 도움말 웹사이트로 이동해보세요!\n\n"
                "앞으로도 유저분들을 위한 Bean World가 되겠습니다! 감사합니다!"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, view=DonateView(), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

def validate_updates_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            updates = json.load(file)
        
        for update in updates:
            if not all(key in update for key in ("version", "date", "details")):
                return False
            if not isinstance(update['version'], str):
                return False
            if not isinstance(update['date'], str):
                return False
            if not isinstance(update['details'], list) or not all(isinstance(detail, str) for detail in update['details']):
                return False
        
        return True
    except (json.JSONDecodeError, FileNotFoundError):
        return False

previous_net_io = None

def calculate_network_usage():
    global previous_net_io
    current_net_io = psutil.net_io_counters()
    
    if previous_net_io is None:
        previous_net_io = current_net_io
        return 0, 0
    
    sent_mb = (current_net_io.bytes_sent - previous_net_io.bytes_sent) * 8 / (10 * 60 * 1024 * 1024)  # 10분 동안의 평균 Mbps로 변환
    recv_mb = (current_net_io.bytes_recv - previous_net_io.bytes_recv) * 8 / (10 * 60 * 1024 * 1024)  # 10분 동안의 평균 Mbps로 변환
    
    previous_net_io = current_net_io
    return sent_mb, recv_mb

@bot.tree.command(name="시스템", description="현재 시스템 상태를 표시합니다.")
@app_commands.guild_only()
async def system_status(interaction: discord.Interaction):
    try:
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles] and str(interaction.user.id) not in USER_IDS:
            await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        # CPU 사용률
        cpu_usage = psutil.cpu_percent(interval=1)

        # 메모리 사용량
        memory_info = psutil.virtual_memory()
        total_memory = memory_info.total // (1024 * 1024)
        used_memory = memory_info.used // (1024 * 1024)
        free_memory = memory_info.available // (1024 * 1024)
        memory_percent = memory_info.percent

        # 디스크 사용량
        disk_info = psutil.disk_usage('/')
        total_disk = disk_info.total // (1024 * 1024 * 1024)
        used_disk = disk_info.used // (1024 * 1024 * 1024)
        free_disk = disk_info.free // (1024 * 1024 * 1024)
        disk_percent = disk_info.percent

        # 네트워크 사용량 (Mbps)
        sent_mbps, recv_mbps = calculate_network_usage()

        embed = discord.Embed(title="📊 시스템 상태", color=discord.Color.blue())
        embed.add_field(name="CPU 사용률", value=f"{cpu_usage}%", inline=False)
        embed.add_field(name="메모리 사용량", value=f"총 메모리: {total_memory} MB\n사용된 메모리: {used_memory} MB\n남은 메모리: {free_memory} MB\n사용률: {memory_percent}%", inline=False)
        embed.add_field(name="디스크 사용량", value=f"총 디스크: {total_disk} GB\n사용된 디스크: {used_disk} GB\n남은 디스크: {free_disk} GB\n사용률: {disk_percent}%", inline=False)
        embed.add_field(name="네트워크 사용량", value=f"보낸 데이터: {sent_mbps:.2f} Mbps\n받은 데이터: {recv_mbps:.2f} Mbps", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

@tasks.loop(minutes=10)
async def monitor_system():
    try:
        # CPU 사용률
        cpu_usage = psutil.cpu_percent(interval=1)

        # 메모리 사용량
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent

        # 디스크 사용량
        disk_info = psutil.disk_usage('/')
        disk_percent = disk_info.percent

        # 네트워크 사용량 (Mbps)
        sent_mbps, recv_mbps = calculate_network_usage()

        alert_messages = []

        if cpu_usage > 90:
            alert_messages.append(f"CPU 사용률이 90%를 초과했습니다. 현재 사용률: {cpu_usage}%")

        if memory_percent > 90:
            alert_messages.append(f"메모리 사용률이 90%를 초과했습니다. 현재 사용률: {memory_percent}%")

        if disk_percent > 90:
            alert_messages.append(f"디스크 사용률이 90%를 초과했습니다. 현재 사용률: {disk_percent}%")

        if sent_mbps > 90 or recv_mbps > 900:  # 네트워크 사용량 알림 조건 설정 (100 Mbps 이상)
            alert_messages.append(f"네트워크 사용량이 높습니다. 보낸 데이터: {sent_mbps:.2f} Mbps, 받은 데이터: {recv_mbps:.2f} Mbps")

        if alert_messages:
            for user_id in USER_IDS:
                alert_user = await bot.fetch_user(user_id)
                alert_embed = discord.Embed(title="⚠️ 시스템 알림", color=discord.Color.red())
                for msg in alert_messages:
                    alert_embed.add_field(name="경고", value=msg, inline=False)
                await alert_user.send(embed=alert_embed)
    except Exception as e:
        print(f"시스템 모니터링 중 오류 발생: {e}")

@monitor_system.before_loop
async def before_monitor_system():
    await bot.wait_until_ready()

@bot.tree.command(name="내통계", description="내 게임 통계를 표시합니다.")
@app_commands.guild_only()
async def my_stats_command(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        c.execute("SELECT * FROM game_stats WHERE user_id = ?", (user_id,))
        row = c.fetchone()

        # 기본값으로 초기화된 통계
        stats = {
            'user_id': user_id,
            'rps_wins': 0, 'rps_losses': 0, 'rps_ties': 0, 'rps_net_coins': 0,
            'odd_even_wins': 0, 'odd_even_losses': 0, 'odd_even_net_coins': 0,
            'slot_machine_wins': 0, 'slot_machine_losses': 0, 'slot_machine_net_coins': 0,
            'blackjack_wins': 0, 'blackjack_losses': 0, 'blackjack_ties': 0, 'blackjack_net_coins': 0,
            'check_in_count': 0, 'work_count': 0, 'problem_count': 0,
            'check_in_net_coins': 0  
        }

        if row:
            keys = list(stats.keys())
            if len(row) != len(keys):
                return
            for i in range(1, len(row)):  # 첫 번째 값인 user_id는 건너뜁니다.
                stats[keys[i]] = row[i]

        c.execute("SELECT check_in_count FROM attendance WHERE user_id = ?", (user_id,))
        attendance_row = c.fetchone()
        check_in_count = attendance_row[0] if attendance_row else 0

        embed = discord.Embed(title="📊 내 통계", color=discord.Color.blue())
        embed.add_field(name="✂️ 가위바위보", value=f"승리: {stats['rps_wins']} 패배: {stats['rps_losses']} 무승부: {stats['rps_ties']}\n순 코인: {stats['rps_net_coins']} 🪙", inline=True)
        embed.add_field(name="⚖️ 홀짝", value=f"승리: {stats['odd_even_wins']} 패배: {stats['odd_even_losses']}\n순 코인: {stats['odd_even_net_coins']} 🪙", inline=True)
        embed.add_field(name="🎰 슬롯 머신", value=f"승리: {stats['slot_machine_wins']} 패배: {stats['slot_machine_losses']}\n순 코인: {stats['slot_machine_net_coins']} 🪙", inline=True)
        embed.add_field(name="🃏 블랙잭", value=f"승리: {stats['blackjack_wins']} 패배: {stats['blackjack_losses']} 무승부: {stats['blackjack_ties']}\n순 코인: {stats['blackjack_net_coins']} 🪙", inline=True)
        embed.add_field(name="📅 출석 체크", value=f"출석 횟수: {check_in_count}", inline=True)
        embed.add_field(name="💼 돈 벌기", value=f"노가다: {stats['work_count']} 문제풀기: {stats['problem_count']}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.source = source  # 추가된 라인

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
    
@bot.event
async def on_ready():
    print(f'{bot.user.name}로 로그인했습니다. (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'명령어 동기화 중 오류 발생: {e}')

@bot.tree.command(name="입장", description="봇을 음성 채널로 호출합니다.")
async def join(interaction: discord.Interaction):
    # 사용자가 음성 채널에 있는지 확인
    if not interaction.user.voice:
        await interaction.response.send_message(embed=discord.Embed(description="먼저 음성 채널에 들어가 주세요!", color=discord.Color.red()), ephemeral=True)
        return
    
    channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        # 봇이 아직 음성 채널에 없으면, 사용자가 있는 채널로 연결
        await channel.connect()
        await interaction.response.send_message(embed=discord.Embed(description=f"'{channel.name}' 채널에 입장했습니다."), ephemeral=True)
    elif voice_client.channel != channel:
        # 봇이 다른 음성 채널에 있을 경우
        await interaction.response.send_message(embed=discord.Embed(description="현재 다른 통화방에서 노래를 재생 중이예요!", color=discord.Color.red()), ephemeral=True)
    else:
        # 봇이 이미 해당 채널에 있는 경우
        await interaction.response.send_message(embed=discord.Embed(description="봇이 이미 음성 채널에 있습니다."), ephemeral=True)
    
@bot.tree.command(name="떠나기", description="봇을 음성 채널에서 나가게 합니다.")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message(embed=discord.Embed(description="음성 채널에서 나갔습니다."), ephemeral=True)
        await clear_playing_message(interaction.guild.id)
    else:
        await interaction.response.send_message(embed=discord.Embed(description="봇이 음성 채널에 연결되어 있지 않습니다.", color=discord.Color.red()), ephemeral=True)

# 서버별 재생 목록을 저장할 큐
bot.song_queues = {}
bot.playing_messages = {}

async def search_youtube(query):
    ytdl_search_options = ytdl_format_options.copy()
    ytdl_search_options['default_search'] = 'ytsearch'
    ytdl_search = youtube_dl.YoutubeDL(ytdl_search_options)
    search_result = ytdl_search.extract_info(query, download=False)
    if 'entries' in search_result:
        return search_result['entries'][0]['webpage_url']
    return None

# 스킵 명령어
@bot.tree.command(name="스킵", description="현재 재생 중인 곡을 건너뜁니다.")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = interaction.guild.id

    if voice_client and voice_client.is_playing():
        voice_client.stop()  # 현재 곡 중지 -> 다음 곡 재생

        # 반복 재생 모드 해제
        bot.repeat_mode[guild_id] = False

        await interaction.response.send_message(embed=discord.Embed(description="현재 곡을 건너뛰고 반복 재생 모드를 해제했습니다.", color=discord.Color.green()), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(description="현재 재생 중인 음악이 없습니다.", color=discord.Color.red()), ephemeral=True)

# 자동 퇴장 타이머 함수 (중복 방지 및 재생 중 타이머 실행 방지)
async def auto_disconnect_timer(voice_client, interaction):
    guild_id = interaction.guild.id

    # 타이머가 이미 실행 중이라면 실행하지 않음
    if bot.disconnect_timer_active.get(guild_id):
        return

    bot.disconnect_timer_active[guild_id] = True  # 타이머 활성화 플래그 설정
    timer = 300  # 5분 (300초)
    await asyncio.sleep(timer)

    # 봇이 여전히 음성 채널에 있고, 노래를 재생하지 않으면 자동 퇴장
    if voice_client.is_connected() and (not voice_client.is_playing() or len(voice_client.channel.members) == 1):
        await voice_client.disconnect()

        # 임베드 메시지 생성
        embed = discord.Embed(
            title="자동 퇴장",
            description="5분간 실행된 작업이 없어 음성 채널에서 퇴장했어요!",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)

    # 타이머 종료 시 플래그 해제
    bot.disconnect_timer_active[guild_id] = False



# 봇 초기화 시 타이머 플래그도 초기화
bot.disconnect_timer_active = {}

# 서버별 반복 재생 여부를 저장할 변수 추가
bot.repeat_mode = {}

@bot.tree.command(name="반복재생", description="현재 재생 중인 곡을 반복 재생합니다.")
@app_commands.describe(option="반복 여부 설정 (켜기/끄기)")
@app_commands.choices(option=[
    app_commands.Choice(name="켜기", value="켜기"),
    app_commands.Choice(name="끄기", value="끄기")
])
async def repeat(interaction: discord.Interaction, option: app_commands.Choice[str]):
    guild_id = interaction.guild.id

    if option.value == "켜기":
        bot.repeat_mode[guild_id] = True
        
        # 현재 재생 중인 곡이 있으면 그 곡을 큐에 추가
        if guild_id in bot.currently_playing:
            current_song = bot.currently_playing[guild_id]
            bot.song_queues[guild_id].insert(0, current_song)

        await interaction.response.send_message(embed=discord.Embed(description="반복 재생이 **켜졌습니다**.", color=discord.Color.green()), ephemeral=True)

    elif option.value == "끄기":
        bot.repeat_mode[guild_id] = False

        # 반복 모드를 끌 때, 큐에 현재 곡이 있는지 확인 후 제거
        if guild_id in bot.song_queues and bot.currently_playing.get(guild_id) in bot.song_queues[guild_id]:
            bot.song_queues[guild_id].remove(bot.currently_playing[guild_id])

        await interaction.response.send_message(embed=discord.Embed(description="반복 재생이 **꺼졌습니다**.", color=discord.Color.red()), ephemeral=True)

@bot.tree.command(name="재생", description="유튜브 URL의 음악을 재생합니다.")
@app_commands.describe(url_or_search="재생할 유튜브 URL 또는 검색어")
async def play(interaction: discord.Interaction, url_or_search: str):
    voice_client = interaction.guild.voice_client
    if not interaction.user.voice:
        await interaction.response.send_message(embed=discord.Embed(description="먼저 음성 채널에 연결되어야 합니다.", color=discord.Color.red()), ephemeral=True)
        return

    channel = interaction.user.voice.channel
    if not voice_client or not voice_client.is_connected():
        await channel.connect()

    voice_client = interaction.guild.voice_client

    await interaction.response.defer(ephemeral=True)

    loop = asyncio.get_event_loop()

    try:
        # URL 또는 검색어 처리
        if not url_or_search.startswith("http"):
            url_or_search = await search_youtube(url_or_search)  # 검색어를 URL로 변환
        
        # URL이 있는 경우에만 추출 시도
        info = await loop.run_in_executor(None, lambda: ytdl.extract_info(url_or_search, download=False))
        title = info.get('title', '제목 없음')
        url = info.get('webpage_url')
        thumbnail = info.get('thumbnail')

        # 재생 목록에 추가
        guild_id = interaction.guild.id
        if guild_id not in bot.song_queues:
            bot.song_queues[guild_id] = []

        bot.song_queues[guild_id].append({'title': title, 'url': url, 'thumbnail': thumbnail})

        # 현재 곡이 재생 중이지 않다면 바로 재생 시작
        if not voice_client.is_playing() and not voice_client.is_paused():
            await play_next_song(interaction)
        else:
            await interaction.followup.send(embed=discord.Embed(description=f"**{title}**이(가) 재생 목록에 추가되었습니다.", color=discord.Color.blue()), ephemeral=True)

    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=f"오류 발생: {str(e)}", color=discord.Color.red()), ephemeral=True)

# 재생목록 명령어 (보기, 삭제) 수정
@bot.tree.command(name="재생목록", description="재생목록을 관리합니다.")
@app_commands.describe(index="삭제할 곡의 번호(삭제 옵션일 경우)")
@app_commands.choices(option=[
    app_commands.Choice(name="보기", value="보기"),
    app_commands.Choice(name="삭제", value="삭제")
])
async def playlist(interaction: discord.Interaction, option: app_commands.Choice[str], index: int = None):
    guild_id = interaction.guild.id

    # 해당 서버에 재생목록이 없다면 생성
    if guild_id not in bot.song_queues:
        bot.song_queues[guild_id] = []

    # "보기" 옵션: 현재 재생목록 확인
    if option.value == "보기":
        if len(bot.song_queues[guild_id]) == 0 and guild_id not in bot.currently_playing:
            await interaction.response.send_message(embed=discord.Embed(description="현재 재생목록이 비어 있습니다.", color=discord.Color.blue()), ephemeral=True)
        else:
            embed = discord.Embed(title="현재 재생목록", color=discord.Color.green())

            # 현재 재생 중인 곡 표시
            if guild_id in bot.currently_playing:
                current_song = bot.currently_playing[guild_id]
                embed.add_field(name="▶️ 현재 재생 중:", value=f"**{current_song['title']}**", inline=False)

            # 대기 중인 곡 목록 표시
            for i, song in enumerate(bot.song_queues[guild_id], start=1):
                embed.add_field(name=f"{i}.", value=song['title'], inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    # "삭제" 옵션: 특정 곡 삭제
    elif option.value == "삭제":
        if len(bot.song_queues[guild_id]) == 0:
            await interaction.response.send_message(embed=discord.Embed(description="재생목록이 비어 있어 삭제할 곡이 없습니다.", color=discord.Color.red()), ephemeral=True)
        elif index is None or index < 1 or index > len(bot.song_queues[guild_id]):
            await interaction.response.send_message(embed=discord.Embed(description="올바른 곡 번호를 입력해주세요.", color=discord.Color.red()), ephemeral=True)
        else:
            removed_song = bot.song_queues[guild_id].pop(index - 1)  # 곡 삭제
            await interaction.response.send_message(embed=discord.Embed(description=f"**{removed_song['title']}** 곡을 재생목록에서 삭제했습니다.", color=discord.Color.green()), ephemeral=True)

# 재생 중인 곡을 저장할 변수 추가
bot.currently_playing = {}

async def play_next_song(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = interaction.guild.id

    # 재생 목록이 없으면 타이머 시작
    if not bot.song_queues.get(guild_id):
        await auto_disconnect_timer(voice_client, interaction)  # 타이머 호출
        return

    # 현재 재생 중이거나 일시정지 상태일 때는 다음 곡을 재생하지 않음
    if voice_client.is_playing() or voice_client.is_paused():
        return

    # 큐에서 다음 곡을 꺼내서 재생
    if bot.song_queues[guild_id]:
        next_song = bot.song_queues[guild_id].pop(0)  # 큐에서 곡 제거
        player = await YTDLSource.from_url(next_song['url'], loop=bot.loop, stream=True)  # 다음 곡 불러오기

        # 반복 재생 모드가 켜져 있으면, 현재 곡을 큐에 다시 추가
        if bot.repeat_mode.get(guild_id, False):
            bot.song_queues[guild_id].insert(0, next_song)

        # 현재 재생 중인 곡 정보를 저장
        bot.currently_playing[guild_id] = {
            'title': player.title,
            'url': next_song['url'],
            'thumbnail': next_song['thumbnail']
        }

        # 플레이어 실행 및 다음 곡 재생 준비
        voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(interaction), bot.loop).result())

        # 재생 중인 노래를 메시지로 표시
        embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
        if player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)

        try:
            # 상호작용에 대한 응답이 완료되었는지 확인 후 메시지 전송
            if interaction.response.is_done():
                playing_message = await interaction.followup.send(embed=embed)
            else:
                playing_message = await interaction.response.send_message(embed=embed)
            
            # 재생 메시지를 봇이 관리
            bot.playing_messages[guild_id] = playing_message
        except Exception as e:
            print(f"재생 메시지 전송 중 오류: {str(e)}")

    # 노래가 끝나면 자동 퇴장 타이머 실행
    if not bot.song_queues[guild_id]:
        await auto_disconnect_timer(voice_client, interaction)

async def play_specific_song(interaction: discord.Interaction, url: str):
    voice_client = interaction.guild.voice_client
    try:
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(clear_playing_message(interaction.guild.id), bot.loop).result())
        
        embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
        
        if player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)
        
        playing_message = await interaction.followup.send(embed=embed)
        bot.playing_messages[interaction.guild.id] = playing_message
    
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=f"오류 발생: {str(e)}", color=discord.Color.red()), ephemeral=True)

async def play_all_songs(interaction: discord.Interaction, urls: list):
    voice_client = interaction.guild.voice_client
    try:
        for url in urls:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(clear_playing_message(interaction.guild.id), bot.loop).result())
            embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
            playing_message = await interaction.followup.send(embed=embed)
            bot.playing_messages[interaction.guild.id] = playing_message
            await asyncio.sleep(player.data['duration'])  # 노래 길이만큼 대기
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=f"오류 발생: {str(e)}", color=discord.Color.red()), ephemeral=True)

@bot.tree.command(name="일시정지", description="음악을 일시 정지합니다.")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = interaction.guild.id

    if voice_client and voice_client.is_playing():
        voice_client.pause()

        # 반복 재생 모드 해제
        bot.repeat_mode[guild_id] = False

        await interaction.response.send_message(embed=discord.Embed(description="음악을 일시 정지하고 반복 재생 모드를 해제했습니다."), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(description="현재 재생 중인 음악이 없습니다.", color=discord.Color.red()), ephemeral=True)

@bot.tree.command(name="다시재생", description="일시 정지된 음악을 다시 재생합니다.")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message(embed=discord.Embed(description="음악을 다시 재생했습니다."), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(description="일시 정지된 음악이 없습니다.", color=discord.Color.red()), ephemeral=True)

@bot.tree.command(name="정지", description="음악을 정지합니다.")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = interaction.guild.id

    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message(embed=discord.Embed(description="봇이 음성 채널에 연결되어 있지 않습니다.", color=discord.Color.red()), ephemeral=True)
        return

    if voice_client.is_playing() or voice_client.is_paused():
        voice_client.stop()

        # 반복 재생 모드 해제
        bot.repeat_mode[guild_id] = False

        # 재생 중인 메시지 클리어
        await clear_playing_message(guild_id)

        await interaction.response.send_message(embed=discord.Embed(description="음악이 정지되었습니다. 반복 재생 모드가 해제되었습니다.", color=discord.Color.red()), ephemeral=True)
    else:
        await interaction.response.send_message(embed=discord.Embed(description="현재 재생 중인 음악이 없습니다.", color=discord.Color.red()), ephemeral=True)

async def clear_playing_message(guild_id):
    if guild_id in bot.playing_messages:
        message = bot.playing_messages[guild_id]
        try:
            await message.delete()
        except discord.NotFound:
            pass
        del bot.playing_messages[guild_id]

bot.playing_messages = {}

print(nacl.__version__)

# 봇 준비
@bot.event
async def on_ready():
    try:
        #명령어 실행
        hangang(bot)
        ping(bot)
        sponsor(bot)
        announcement(bot)
        banned_word(bot)
        timeout(bot)
        ban(bot)
        event(bot)
        attendance_check(bot)
        attendance_ranking(bot)
        blackjack_help(bot)
        odd_even(bot)
        update(bot)

        # 사용자 코인 관련 컬럼이 있는지 확인하는 함수 호출
        ensure_check_in_net_coins_column()

        # updates.json 파일의 무결성 검사
        updates_file = 'updates.json'
        if not validate_updates_json(updates_file):
            print(f"업데이트 JSON 파일 ({updates_file})의 무결성 검사가 실패했습니다. 파일을 확인하세요.")
            await bot.close()
            return

        # 명령어 동기화 시도 (예외 처리 추가)
        synced = await bot.tree.sync()
        print(f"명령어가 동기화되었습니다. 동기화된 명령어 개수: {len(synced)}개")

        # 봇의 현재 상태 메시지 설정
        await bot.change_presence(activity=discord.Game(name="명령어 도움은 /도움말"))

        # 시스템 모니터링 시작
        monitor_system.start()

        print(f'지금부터 서버 관리를 시작합니다! 봇 {bot.user}')

        # 주식 가격 업데이트 루프 실행 (봇 시작 후 30분 대기)
        await asyncio.sleep(1800)
        update_stock_prices.start()

    except discord.errors.HTTPException as http_err:
        print(f"HTTP 오류 발생: {http_err}")
    except discord.errors.Forbidden as forbidden_err:
        print(f"권한 오류 발생: {forbidden_err}")
    except Exception as e:
        print(f"명령어 동기화 중 알 수 없는 오류 발생: {e}")

# 봇 실행
bot.run(TOKEN)
