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

# Discord 봇 설정
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

youtube_dl.utils.bug_reports_message = lambda: ''

# .env 파일에서 환경 변수를 로드합니다
load_dotenv()

# 환경 변수를 불러옵니다
TOKEN = os.getenv('DISCORD_TOKEN')
ANNOUNCEMENT_CHANNEL_ID = os.getenv('ANNOUNCEMENT_CHANNEL_ID')
ADMIN_ROLE_ID = os.getenv('ADMIN_ROLE_ID')
USER_IDS = os.getenv('USER_IDS').split(',')

# 환경 변수가 제대로 로드되었는지 확인합니다
if TOKEN is None:
    raise ValueError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
if ANNOUNCEMENT_CHANNEL_ID is None:
    raise ValueError("ANNOUNCEMENT_CHANNEL_ID 환경 변수가 설정되지 않았습니다.")
if ADMIN_ROLE_ID is None:
    raise ValueError("ADMIN_ROLE_ID 환경 변수가 설정되지 않았습니다.")
if not USER_IDS:
    raise ValueError("USER_IDS 환경 변수가 설정되지 않았습니다.")

KST = pytz.timezone('Asia/Seoul')

# ANNOUNCEMENT_CHANNEL_ID, ADMIN_ROLE_ID 및 SYSTEM_USER_ID를 정수로 변환합니다
ANNOUNCEMENT_CHANNEL_ID = int(ANNOUNCEMENT_CHANNEL_ID)
ADMIN_ROLE_ID = int(ADMIN_ROLE_ID)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

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

# yt-dlp 포맷 옵션 설정
ytdl_format_options = {
    'format': 'bestaudio[ext=m4a]/bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'ratelimit': '10M',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '32',
    }, {
        'key': 'FFmpegMetadata',
    }],
    'extractor_args': {
        'youtubetab': {
            'skip': ['authcheck']
        }
    }
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -af atempo=1.05,aresample=44100 -sn -dn -bufsize 64M -timeout 10000000 -loglevel info'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# 한강 물 온도 API 클래스
class Hangang:
    ENDPOINT = "https://api.hangang.life/"

    def request(self):
        response = requests.get(self.ENDPOINT, headers={'User-Agent': 'Renyu106/Hangang-API'}, verify=False)
        if response.status_code == 200:
            try:
                json_response = response.json()
                return json_response
            except ValueError as e:
                return None
        else:
            return None

    def get_info(self):
        response = self.request()
        if response and 'STATUS' in response and response['STATUS'] == "OK":
            hangang_data = response['DATAs']['DATA']['HANGANG']
            if '선유' in hangang_data:
                data = hangang_data['선유']
                return {
                    'status': "ok",
                    'temp': data['TEMP'],
                    'last_update': data['LAST_UPDATE'],
                    'ph': data['PH']
                }
            else:
                return {
                    'status': "error",
                    'msg': "선유 데이터를 찾을 수 없습니다."
                }
        else:
            return {
                'status': "error",
                'msg': "API를 불러오는데 실패했습니다."
            }

def get_korean_time():
    return datetime.now(KST)

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

def get_user_coins(user_id: int) -> int:
    c.execute("SELECT coins FROM user_coins WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

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

def ensure_check_in_net_coins_column():
    c.execute("PRAGMA table_info(game_stats)")
    columns = [info[1] for info in c.fetchall()]
    if 'check_in_net_coins' not in columns:
        c.execute("ALTER TABLE game_stats ADD COLUMN check_in_net_coins INTEGER DEFAULT 0")
    conn.commit()

def ensure_user_stats_exist(user_id):
    c.execute("SELECT 1 FROM game_stats WHERE user_id = ?", (user_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO game_stats (user_id) VALUES (?)", (user_id,))
        conn.commit()

def update_rps_stats(user_id, result, bet):
    ensure_user_stats_exist(user_id)
    net_coins = 0
    if result == "승리":
        c.execute("UPDATE game_stats SET rps_wins = rps_wins + 1, rps_net_coins = rps_net_coins + ? WHERE user_id = ?", (net_coins, user_id))
    elif result == "패배":
        net_coins = -bet
        c.execute("UPDATE game_stats SET rps_losses = rps_losses + 1, rps_net_coins = rps_net_coins - ? WHERE user_id = ?", (bet, user_id))
    else:
        net_coins = 0
        c.execute("UPDATE game_stats SET rps_ties = rps_ties + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def update_odd_even_stats(user_id, result, bet):
    ensure_user_stats_exist(user_id)
    if result == "승리":
        net_coins = int(bet * 0.5)  # 승리 시 50% 추가
        c.execute("UPDATE game_stats SET odd_even_wins = odd_even_wins + 1, odd_even_net_coins = odd_even_net_coins + ? WHERE user_id = ?", (net_coins, user_id))
    elif result == "패배":
        c.execute("UPDATE game_stats SET odd_even_losses = odd_even_losses + 1, odd_even_net_coins = odd_even_net_coins - ? WHERE user_id = ?", (bet, user_id))
    conn.commit()

def update_slot_machine_stats(user_id, result, payout, bet):
    ensure_user_stats_exist(user_id)
    if result == "승리":
        net_coins = payout - bet
        c.execute("UPDATE game_stats SET slot_machine_wins = slot_machine_wins + 1, slot_machine_net_coins = slot_machine_net_coins + ? WHERE user_id = ?", (net_coins, user_id))
    else:
        c.execute("UPDATE game_stats SET slot_machine_losses = slot_machine_losses + 1, slot_machine_net_coins = slot_machine_net_coins - ? WHERE user_id = ?", (bet, user_id))
    conn.commit()

def update_blackjack_stats(user_id, result, net_coins):
    c.execute("SELECT blackjack_wins, blackjack_losses, blackjack_ties, blackjack_net_coins FROM game_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if row is None:
        wins, losses, ties = 0, 0, 0
        if result == 'win':
            wins = 1
        elif result == 'loss':
            losses = 1
        else:
            ties = 1
        c.execute("INSERT INTO game_stats (user_id, blackjack_wins, blackjack_losses, blackjack_ties, blackjack_net_coins) VALUES (?, ?, ?, ?, ?)", (user_id, wins, losses, ties, net_coins))
    else:
        wins, losses, ties, current_net_coins = row
        if result == 'win':
            wins += 1
        elif result == 'loss':
            losses += 1
        else:
            ties += 1
        c.execute("UPDATE game_stats SET blackjack_wins = ?, blackjack_losses = ?, blackjack_ties = ?, blackjack_net_coins = ? WHERE user_id = ?", (wins, losses, ties, current_net_coins + net_coins, user_id))
    conn.commit()

def update_daily_tasks(user_id, task_type):
    current_time = get_korean_time()
    ensure_user_stats_exist(user_id)

    c.execute("SELECT last_reset, work_count, problem_count FROM daily_tasks WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if row:
        last_reset_time = datetime.fromisoformat(row[0]).astimezone(KST)
        if (current_time - last_reset_time).total_seconds() >= 86400:
            c.execute("UPDATE daily_tasks SET last_reset = ?, work_count = 0, problem_count = 0 WHERE user_id = ?", (current_time.isoformat(), user_id))
            conn.commit()

    if task_type == "노가다":
        c.execute("UPDATE daily_tasks SET work_count = work_count + 1 WHERE user_id = ?", (user_id,))
        c.execute("UPDATE game_stats SET work_count = work_count + 1 WHERE user_id = ?", (user_id,))
    elif task_type == "문제풀기":
        c.execute("UPDATE daily_tasks SET problem_count = problem_count + 1 WHERE user_id = ?", (user_id,))
        c.execute("UPDATE game_stats SET problem_count = problem_count + 1 WHERE user_id = ?", (user_id,))
    
    conn.commit()

def update_blackjack_stats(user_id, result, net_coins):
    c.execute("SELECT blackjack_wins, blackjack_losses, blackjack_ties, blackjack_net_coins FROM game_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if row is None:
        wins, losses, ties = 0, 0, 0
        if result == 'win':
            wins = 1
        elif result == 'loss':
            losses = 1
        else:
            ties = 1
        c.execute("INSERT INTO game_stats (user_id, blackjack_wins, blackjack_losses, blackjack_ties, blackjack_net_coins) VALUES (?, ?, ?, ?, ?)", (user_id, wins, losses, ties, net_coins))
    else:
        wins, losses, ties, current_net_coins = row
        if result == 'win':
            wins += 1
        elif result == 'loss':
            losses += 1
        else:
            ties += 1
        c.execute("UPDATE game_stats SET blackjack_wins = ?, blackjack_losses = ?, blackjack_ties = ?, blackjack_net_coins = ? WHERE user_id = ?", (wins, losses, ties, current_net_coins + net_coins, user_id))
    conn.commit()


@bot.tree.command(name="한강물온도", description="현재 한강 물 온도를 표시합니다. (음악 듣는 중에 사용해 보세요!)")
@app_commands.guild_only()
async def hangang_temp_command(interaction: discord.Interaction):
    try:
        hangang = Hangang()
        info = hangang.get_info()

        if info['status'] == "ok":
            embed = discord.Embed(title="한강물 온도", color=discord.Color.blue())
            embed.add_field(name="한강", value=f"온도: {info['temp']} °C\n마지막 업데이트: {info['last_update']}\nPH: {info['ph']}", inline=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(info['msg'], ephemeral=True)
    except Exception as e:
        print(f"명령어 처리 중 오류 발생: {e}")
        await interaction.response.send_message("명령어를 처리하는 중 오류가 발생했습니다.", ephemeral=True)

# 핑 명령어
@bot.tree.command(name="핑", description="서버의 핑을 확인합니다.")
@app_commands.guild_only()
async def ping_command(interaction: discord.Interaction):
    try:
        latency = round(bot.latency * 1000)
        start_time = datetime.utcnow()
        await interaction.response.send_message("핑을 확인하는 중...", ephemeral=True)
        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000

        embed = discord.Embed(
            title="🏓 퐁!",
            description=(
                f"현재 핑: {latency}ms\n"
                f"명령어 응답 시간: {response_time:.2f}ms\n"
                f"레이턴시: {latency + response_time:.2f}ms"
            ),
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)

# 후원 명령어
class DonateView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="💻개발자 후원", url="https://buymeacoffee.com/ilbie"))

@bot.tree.command(name="후원", description="후원 정보를 제공합니다.")
@app_commands.guild_only()
async def donate_command(interaction: discord.Interaction):
    try:
        embed = discord.Embed(
            title="후원 안내",
            description=(
                "안녕하세요! 봇 개발 및 서버 운영을 위해 후원을 받고 있습니다.\n"
                "후원해주시면 큰 도움이 됩니다!\n\n"
                "**후원 방법:**\n\n"
                "아래 버튼을 통해 후원해주시면 감사하겠습니다!\n\n"
                "감사합니다! ;)"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, view=DonateView(), ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)


#공지
@bot.tree.command(name="공지", description="공지사항을 전송합니다.")
@app_commands.describe(메시지="전송할 공지 내용을 입력하세요.", 역할들="멘션할 역할을 공백으로 구분하여 입력하세요.")
@app_commands.guild_only()
async def announce_command(interaction: discord.Interaction, 메시지: str, 역할들: str = ""):
    try:
        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("공지 채널을 찾을 수 없습니다. 채널 ID를 확인하세요.", ephemeral=True)
            return
        
        role_mentions = []
        if 역할들:
            role_ids = 역할들.split()
            guild = interaction.guild
            for role_id in role_ids:
                role_id = role_id.strip('<@&>')
                if role_id.isdigit():
                    role = guild.get_role(int(role_id))
                    if role:
                        role_mentions.append(f"||{role.mention}||")
                    else:
                        await interaction.response.send_message(f"역할 ID '{role_id}'을(를) 찾을 수 없습니다.", ephemeral=True)
                        return
        
        role_mentions_text = ' '.join(role_mentions) if role_mentions else ""
        
        embed = discord.Embed(
            title="📢 공지사항",
            description=메시지,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"작성자: {interaction.user.name}", icon_url=interaction.user.avatar.url)
        
        await channel.send(content=role_mentions_text, embed=embed)
        await interaction.response.send_message("공지가 전송되었습니다.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

# 금지 단어 관리 명령어
@bot.tree.command(name="금지단어", description="금지된 단어를 관리합니다.")
@app_commands.choices(옵션=[
    app_commands.Choice(name="추가", value="추가"),
    app_commands.Choice(name="삭제", value="삭제"),
    app_commands.Choice(name="리스트", value="리스트")
])
@app_commands.describe(옵션="동작을 선택하세요 (추가, 삭제, 리스트).", 단어="금지할 단어를 입력하세요.")
@app_commands.guild_only()
async def ban_word_command(interaction: discord.Interaction, 옵션: app_commands.Choice[str], 단어: str = None):
    try:
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        if 옵션.value == "추가" and 단어:
            c.execute("INSERT INTO banned_words (word) VALUES (?)", (단어,))
            conn.commit()
            await interaction.response.send_message(f"금지된 단어 '{단어}'가 추가되었습니다.", ephemeral=True)
        elif 옵션.value == "삭제" and 단어:
            c.execute("SELECT word FROM banned_words WHERE word = ?", (단어,))
            if c.fetchone() is None:
                await interaction.response.send_message(f"금지된 단어 '{단어}'가 데이터베이스에 없습니다.", ephemeral=True)
            else:
                c.execute("DELETE FROM banned_words WHERE word = ?", (단어,))
                conn.commit()
                await interaction.response.send_message(f"금지된 단어 '{단어}'가 삭제되었습니다.", ephemeral=True)
        elif 옵션.value == "리스트":
            c.execute("SELECT word FROM banned_words")
            banned_words = [row[0] for row in c.fetchall()]
            if banned_words:
                banned_words_text = " | ".join(banned_words)
                embed = discord.Embed(title="금지된 단어 목록", description=banned_words_text, color=discord.Color.red())
            else:
                embed = discord.Embed(title="금지된 단어 목록", description="등록된 금지된 단어가 없습니다.", color=discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("잘못된 명령어 사용입니다. 사용법: /밴단어 추가 <단어>, /밴단어 삭제 <단어>, /밴단어 리스트", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

# 타임아웃 명령어
@bot.tree.command(name="타임아웃", description="사용자를 타임아웃합니다.")
@app_commands.describe(사용자="타임아웃할 사용자를 선택하세요.", 기간="타임아웃 기간을 입력하세요 (예: 1d, 1h, 10m).", 이유="타임아웃 사유를 입력하세요.")
@app_commands.guild_only()
async def timeout_command(interaction: discord.Interaction, 사용자: discord.Member, 기간: str, 이유: str = None):
    try:
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return
        
        duration_map = {'d': '일', 'h': '시간', 'm': '분'}
        unit = 기간[-1]

        if unit not in duration_map:
            await interaction.response.send_message("기간 형식이 잘못되었습니다. 'd', 'h', 'm' 중 하나를 사용하세요.", ephemeral=True)
            return

        try:
            value = int(기간[:-1])
        except ValueError:
            await interaction.response.send_message("기간의 숫자 부분이 잘못되었습니다. 올바른 숫자를 입력하세요.", ephemeral=True)
            return

        if unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'm':
            delta = timedelta(minutes=value)

        timeout_end = discord.utils.utcnow() + delta

        try:
            await 사용자.edit(timed_out_until=timeout_end)
        except discord.Forbidden:
            await interaction.response.send_message("타임아웃할 권한이 없습니다.", ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"타임아웃 처리 중 오류가 발생했습니다", ephemeral=True)
            return

        try:
            await 사용자.send(
                embed=discord.Embed(
                    title="타임아웃 알림",
                    description=(
                        f"서버에서 {value}{duration_map[unit]}동안 타임아웃 되었습니다."
                        + (f"\n이유: {이유}" if 이유 else "")
                    ),
                    color=discord.Color.red()
                )
            )
        except discord.Forbidden:
            print(f"{사용자}에게 DM을 보낼 수 없습니다.")

        embed = discord.Embed(
            title="타임아웃 알림",
            description=(
                f"{사용자.mention}님이 {value}{duration_map[unit]}동안 타임아웃 되었습니다."
                + (f"\n이유: {이유}" if 이유 else "")
            ),
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("타임아웃이 성공적으로 적용되었습니다.", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"예기치 못한 오류가 발생했습니다: {str(e)}", ephemeral=True)

# 밴 명령어
@bot.tree.command(name="밴", description="사용자를 차단합니다.")
@app_commands.describe(사용자="차단할 사용자를 선택하세요.", 이유="차단 사유를 입력하세요.")
@app_commands.guild_only()
async def ban_command(interaction: discord.Interaction, 사용자: discord.Member, 이유: str = None):
    try:
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        try:
            await 사용자.ban(reason=이유)
        except discord.Forbidden:
            await interaction.response.send_message("사용자를 차단할 권한이 없습니다.", ephemeral=True)
            return
        except discord.HTTPException as e:
            await interaction.response.send_message(f"사용자 차단 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
            return

        embed = discord.Embed(
            title="사용자 차단 알림",
            description=(
                f"{사용자.mention}님이 서버에서 차단되었습니다."
                + (f"\n이유: {이유}" if 이유 else "")
            ),
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("사용자가 성공적으로 차단되었습니다.", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"예기치 못한 오류가 발생했습니다: {str(e)}", ephemeral=True)

# 메시지 검사 및 타임아웃 처리
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        return  # 개인 DM에서는 명령어를 처리하지 않음

    try:
        c.execute("SELECT word FROM banned_words")
        banned_words = [row[0] for row in c.fetchall()]

        for word in banned_words:
            if word in message.content:
                await message.delete()
                timeout_duration = timedelta(days=1)
                timeout_end = discord.utils.utcnow() + timeout_duration

                # 사용자에게 DM을 보내기
                try:
                    await message.author.send(
                        embed=discord.Embed(
                            title="타임아웃 알림",
                            description=(
                                "금지된 단어를 사용하여 1일(24시간) 동안 타임아웃 되었습니다.\n"
                                "오작동 또는 다른 문의가 있을 시 OWNER의 갠디로 문의해주세요."
                            ),
                            color=discord.Color.red()
                        )
                    )
                except discord.Forbidden:
                    print(f"사용자 {message.author}에게 DM을 보낼 수 없습니다.")

                # 타임아웃 적용
                try:
                    await message.author.edit(timed_out_until=timeout_end)
                except discord.Forbidden:
                    print(f"{message.author}에게 타임아웃을 적용할 수 없습니다.")
                    continue  # 타임아웃 적용에 실패하면 다음 금지된 단어로 넘어감

                # 해당 채널에 임베드 메시지 보내기 (사용자 멘션 포함)
                warning_embed = discord.Embed(
                    title="금지된 단어 사용",
                    description=(
                        f"{message.author.mention} 금지된 단어를 사용하여 1일(24시간) 동안 타임아웃 되었습니다."
                    ),
                    color=discord.Color.red()
                )
                warning_message = await message.channel.send(embed=warning_embed)
                
                # 일정 시간 후에 메시지 삭제
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=10))
                await warning_message.delete()

                break
    except Exception as e:
        print(f"오류 발생: {str(e)}")

    await bot.process_commands(message)


# 이벤트 명령어 정의
@bot.tree.command(name="이벤트", description="이벤트를 관리합니다.")
@app_commands.choices(옵션=[
    app_commands.Choice(name="목록", value="목록"),
    app_commands.Choice(name="등록", value="등록"),
    app_commands.Choice(name="삭제", value="삭제"),
    app_commands.Choice(name="참여", value="참여")
])
@app_commands.describe(
    옵션="이벤트 관리 옵션을 선택하세요.",
    이름="이벤트 이름을 입력하세요.",
    일자="이벤트 일자를 입력하세요 (예: 2008-12-05 11:00).",
    종료기간="이벤트 종료 일자를 입력하세요 (예: 2008-12-06 11:00).",
    장소="이벤트 장소를 입력하세요."
)
@app_commands.guild_only()
async def event_command(interaction: discord.Interaction, 옵션: app_commands.Choice[str], 이름: str = None, 일자: str = None, 종료기간: str = None, 장소: str = None):
    try:
        if 옵션.value in ["등록", "삭제"]:
            if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
                await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
                return

        if 옵션.value == "등록" and 이름 and 일자 and 종료기간 and 장소:
            try:
                event_date = datetime.strptime(일자, '%Y-%m-%d %H:%M')
                end_date = datetime.strptime(종료기간, '%Y-%m-%d %H:%M')
            except ValueError:
                await interaction.response.send_message("일자 형식이 잘못되었습니다. 올바른 형식: YYYY-MM-DD HH:MM", ephemeral=True)
                return

            if event_date >= end_date:
                await interaction.response.send_message("종료기간은 시작일자 이후여야 합니다.", ephemeral=True)
                return

            c.execute("INSERT INTO events (name, date, end_date, location, participants) VALUES (?, ?, ?, ?, ?)", (이름, 일자, 종료기간, 장소, ""))
            conn.commit()
            await interaction.response.send_message(f"이벤트 '{이름}'이(가) {일자}에 {장소}에서 시작하며, 종료일은 {종료기간}입니다.", ephemeral=True)
        elif 옵션.value == "삭제" and 이름:
            c.execute("SELECT name FROM events WHERE name = ?", (이름,))
            if c.fetchone() is None:
                await interaction.response.send_message(f"이벤트 '{이름}'가 존재하지 않습니다.", ephemeral=True)
            else:
                c.execute("DELETE FROM events WHERE name = ?", (이름,))
                conn.commit()
                await interaction.response.send_message(f"이벤트 '{이름}'가 삭제되었습니다.", ephemeral=True)
        elif 옵션.value == "참여" and 이름:
            c.execute("SELECT participants FROM events WHERE name = ?", (이름,))
            row = c.fetchone()
            if row is None:
                await interaction.response.send_message(f"이벤트 '{이름}'가 존재하지 않습니다.", ephemeral=True)
            else:
                participants = row[0].split(',') if row[0] else []
                if str(interaction.user.id) in participants:
                    await interaction.response.send_message(f"이미 이벤트 '{이름}'에 참여 중입니다.", ephemeral=True)
                else:
                    participants.append(str(interaction.user.id))
                    c.execute("UPDATE events SET participants = ? WHERE name = ?", (','.join(participants), 이름))
                    conn.commit()
                    await interaction.response.send_message(f"이벤트 '{이름}'에 참여하였습니다.", ephemeral=True)
        elif 옵션.value == "목록":
            c.execute("SELECT name, date, end_date, location, participants FROM events")
            events = c.fetchall()
            now = datetime.now()

            if events:
                embed = discord.Embed(title="이벤트 목록", color=discord.Color.blue())
                for event in events:
                    event_date = datetime.strptime(event[1], '%Y-%m-%d %H:%M')
                    end_date = datetime.strptime(event[2], '%Y-%m-%d %H:%M')
                    if end_date > now:
                        participants_list = [interaction.guild.get_member(int(id)).mention for id in event[4].split(',') if id]
                        participants_text = ', '.join(participants_list) if participants_list else "없음"
                        embed.add_field(
                            name=event[0],
                            value=f"일자: {event[1]}\n종료기간: {event[2]}\n장소: {event[3]}\n참여자: {participants_text}",
                            inline=False
                        )
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message("등록된 이벤트가 없습니다.", ephemeral=True)
        else:
            await interaction.response.send_message("잘못된 명령어 사용입니다. 사용법: /이벤트 목록, /이벤트 등록 <이름> <일자> <종료기간> <장소>, /이벤트 삭제 <이름>, /이벤트 참여 <이름>", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

# 오래된 이벤트 삭제 작업
@tasks.loop(hours=24)
async def remove_past_events():
    now = datetime.now()
    c.execute("SELECT id, end_date FROM events")
    events = c.fetchall()

    for event in events:
        end_date = datetime.strptime(event[1], '%Y-%m-%d %H:%M')
        if end_date < now:
            c.execute("DELETE FROM events WHERE id = ?", (event[0],))
    conn.commit()

# 출석 체크 명령어 
@bot.tree.command(name="출석체크", description="일일 출석 체크로 코인을 획득하고 기록을 남깁니다.")
@app_commands.guild_only()
async def check_in_command(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        current_time = get_korean_time()

        # 사용자 출석 체크 정보 조회
        c.execute("SELECT check_in_count, last_check_in FROM attendance WHERE user_id = ?", (user_id,))
        row = c.fetchone()

        if row:
            check_in_count, last_check_in = row
            last_check_in_time = datetime.fromisoformat(last_check_in).astimezone(KST)
            time_diff = (current_time - last_check_in_time).total_seconds()
            if time_diff < 86400:
                time_remaining = 86400 - time_diff
                hours, remainder = divmod(time_remaining, 3600)
                minutes, seconds = divmod(remainder, 60)
                await interaction.response.send_message(
                    embed=discord.Embed(
                        title="출석체크",
                        description=f"출석 체크는 24시간에 한 번만 가능합니다. 남은 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초",
                        color=discord.Color.red()
                    )
                )
                return

            # 출석 체크 횟수 업데이트 및 마지막 출석 시간 갱신
            check_in_count += 1
            c.execute("UPDATE attendance SET check_in_count = ?, last_check_in = ? WHERE user_id = ?", (check_in_count, current_time.isoformat(), user_id))
        else:
            # 새로운 사용자의 출석 체크 정보 삽입
            check_in_count = 1
            c.execute("INSERT INTO attendance (user_id, check_in_count, last_check_in) VALUES (?, ?, ?)", (user_id, check_in_count, current_time.isoformat()))

        conn.commit()

        # 코인 지급
        update_user_coins(user_id, 100)
        c.execute("UPDATE game_stats SET check_in_net_coins = check_in_net_coins + 100 WHERE user_id = ?", (user_id,))
        conn.commit()

        await interaction.response.send_message(
            embed=discord.Embed(
                title="출석체크",
                description=f"{interaction.user.mention} 출석체크 완료! 100 코인을 받았습니다. 현재 코인: {format_coins(get_user_coins(user_id))}개 🪙 \n현재까지 총 {check_in_count}회 출석체크를 했습니다.",
                color=discord.Color.green()
            )
        )
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

@bot.tree.command(name="출석랭킹", description="출석 랭킹을 표시합니다.")
@app_commands.guild_only()
async def attendance_ranking_command(interaction: discord.Interaction):
    try:
        c.execute("SELECT user_id, check_in_count FROM attendance ORDER BY check_in_count DESC LIMIT 10")
        rankings = c.fetchall()

        if rankings:
            embed = discord.Embed(title="🏆 출석 랭킹", color=discord.Color.blue())
            ranking_text = ""
            rank_emojis = ["🥇", "🥈", "🥉"] + [f"🏅{i+4}" for i in range(7)]
            for i, (user_id, check_in_count) in enumerate(rankings):
                user = await bot.fetch_user(user_id)
                ranking_text += f"{rank_emojis[i]} **{user.name}**: {check_in_count}회\n"
            embed.add_field(name="TOP 10", value=ranking_text, inline=False)
        else:
            embed = discord.Embed(title="🏆 출석 랭킹", description="출석체크 기록이 없습니다.", color=discord.Color.blue())

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

# 삭제 명령어
@bot.tree.command(name="삭제", description="현재 채널의 모든 메시지를 삭제합니다.")
@app_commands.guild_only()
async def clear_channel(interaction: discord.Interaction):
    try:
        if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
            return

        # 먼저 인터랙션에 응답을 보냅니다.
        await interaction.response.send_message("메시지를 삭제하는 중입니다...", ephemeral=True)

        def check(msg):
            return True

        deleted = 0
        while True:
            deleted_msgs = await interaction.channel.purge(limit=50, check=check)
            deleted += len(deleted_msgs)
            if len(deleted_msgs) < 50:
                break
            await asyncio.sleep(1)  # 각 배치 삭제 후 1초 대기

        await interaction.followup.send(f"{deleted}개의 메시지가 삭제되었습니다.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)

# 블랙잭 도움말 명령어
@bot.tree.command(name="블랙잭도움", description="블랙잭 게임의 사용 방법을 안내합니다.")
@app_commands.guild_only()
async def blackjack_help(interaction: discord.Interaction):
    try:
        help_text = (
            "블랙잭 게임 사용법:\n"
            "1. `/블랙잭 <베팅 코인 수>`: 블랙잭 게임을 시작합니다.\n"
            "2. `카드추가`: 플레이어의 손에 카드를 추가합니다.\n"
            "3. `카드유지`: 더 이상 카드를 받지 않고 유지합니다.\n"
            "4. 딜러의 카드와 비교하여 21에 가까운 사람이 승리합니다.\n"
            "5. 승리 시 베팅 코인의 2배를 획득합니다.\n\n"
            "* J, Q, K는 10, A는 11의 숫자를 가지고 있습니다. *"
        )
        embed = discord.Embed(
            title="블랙잭 도움말",
            description=help_text,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

class BlackjackGame:
    def __init__(self, bet, user, user_name):
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.bet = bet
        self.user = user
        self.user_name = user_name
        self.timeout_task = None

    def create_deck(self):
        suits = ['♥️', '♦️', '♣️', '♠️']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(value, suit) for suit in suits for value in values]
        random.shuffle(deck)
        return deck

    def deal_card(self, hand):
        hand.append(self.deck.pop())

    def calculate_hand(self, hand):
        value_dict = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}
        value = sum(value_dict[card[0]] for card in hand)
        num_aces = sum(1 for card in hand if card[0] == 'A')
        while value > 21 and num_aces:
            value -= 10
            num_aces -= 1
        return value

    def player_turn(self):
        return self.calculate_hand(self.player_hand) < 21

    def dealer_turn(self):
        return self.calculate_hand(self.dealer_hand) < 17

    def check_winner(self):
        player_value = self.calculate_hand(self.player_hand)
        dealer_value = self.calculate_hand(self.dealer_hand)
        if dealer_value > 21 or (player_value <= 21 and player_value > dealer_value):
            return '플레이어 승리! 🎉'
        elif player_value > 21 or dealer_value > player_value:
            return '딜러 승리! 😢'
        else:
            return '무승부! 😐'
    
async def handle_timeout(interaction: discord.Interaction, game: BlackjackGame):
    await asyncio.sleep(60)  # 60초 대기
    if not game.game_over:
        game.game_over = True
        result = "타임아웃으로 패배! 😢"
        await show_hands(interaction, game)
        await interaction.followup.send(embed=discord.Embed(
            title="🃏 블랙잭 게임 결과",
            description=f"게임 종료! 타임아웃으로 자동 종료되었습니다. 결과: {result} \n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
            color=discord.Color.red()
        ))

# bot 객체에 blackjack_games 속성을 추가합니다.
bot.blackjack_games = {}

# 블랙잭 명령어
@bot.tree.command(name="블랙잭", description="블랙잭 게임을 시작합니다.")
@app_commands.describe(bet="베팅할 코인 수")
@app_commands.guild_only()
async def blackjack_command(interaction: discord.Interaction, bet: int):
    try:
        user_id = interaction.user.id
        user = interaction.user
        user_name = interaction.user.display_name

        if bet > get_user_coins(user_id):
            await interaction.response.send_message("베팅할 코인이 부족합니다.", ephemeral=True)
            return
        update_user_coins(user_id, -bet)
        game = BlackjackGame(bet, user, user_name)
        game.deal_card(game.player_hand)
        game.deal_card(game.dealer_hand)
        game.deal_card(game.player_hand)
        game.deal_card(game.dealer_hand)
        bot.blackjack_games[user_id] = game
        await show_hands(interaction, game, initial=True)

        # 타임아웃 설정
        game.timeout_task = asyncio.create_task(handle_timeout(interaction, game))
    except Exception as e:
        try:
            await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)
        except discord.errors.NotFound:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

class BlackjackView(discord.ui.View):
    def __init__(self, game, interaction: discord.Interaction):
        super().__init__()
        self.game = game
        self.interaction = interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("이 게임은 당신이 시작한 게임이 아닙니다.", ephemeral=True)
            return False
        if self.game.game_over:
            await interaction.response.send_message("이미 종료된 게임입니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="카드 추가", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_hit(interaction)

    @discord.ui.button(label="카드 유지", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_stand(interaction)

    async def handle_hit(self, interaction: discord.Interaction):
        game = bot.blackjack_games.get(interaction.user.id)
        if game is None:
            await interaction.response.send_message("블랙잭 게임을 먼저 시작하세요. /블랙잭 명령어를 사용하세요.", ephemeral=True)
            return
        game.deal_card(game.player_hand)
        if not game.player_turn():
            game.game_over = True
            while game.dealer_turn():
                game.deal_card(game.dealer_hand)
            result = game.check_winner()
            net_coins = game.bet if result == '플레이어 승리! 🎉' else -game.bet if result == '딜러 승리! 😢' else 0
            update_blackjack_stats(game.user.id, 'win' if result == '플레이어 승리! 🎉' else 'loss' if result == '딜러 승리! 😢' else 'tie', net_coins)
            await show_hands(interaction, game)
            if result == '플레이어 승리! 🎉':
                update_user_coins(interaction.user.id, game.bet * 2)
            elif result == '무승부! 😐':
                update_user_coins(interaction.user.id, game.bet)
            await interaction.followup.send(embed=discord.Embed(
                title="🃏 블랙잭 게임 결과",
                description=f"게임 종료! 결과: {result}\n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
                color=discord.Color.green()
            ))
        else:
            await show_hands(interaction, game)

        # 타임아웃 리셋
        if game.timeout_task:
            game.timeout_task.cancel()
        game.timeout_task = asyncio.create_task(handle_timeout(interaction, game))

    async def handle_stand(self, interaction: discord.Interaction):
        game = bot.blackjack_games.get(interaction.user.id)
        if game is None:
            await interaction.response.send_message("블랙잭 게임을 먼저 시작하세요. /블랙잭 명령어를 사용하세요.", ephemeral=True)
            return
        while game.dealer_turn():
            game.deal_card(game.dealer_hand)
        game.game_over = True
        result = game.check_winner()
        net_coins = game.bet if result == '플레이어 승리! 🎉' else -game.bet if result == '딜러 승리! 😢' else 0
        update_blackjack_stats(game.user.id, 'win' if result == '플레이어 승리! 🎉' else 'loss' if result == '딜러 승리! 😢' else 'tie', net_coins)
        await show_hands(interaction, game)
        if result == '플레이어 승리! 🎉':
            update_user_coins(interaction.user.id, game.bet * 2)
        elif result == '무승부! 😐':
            update_user_coins(interaction.user.id, game.bet)
        await interaction.followup.send(embed=discord.Embed(
            title="🃏 블랙잭 게임 결과",
            description=f"게임 종료! 결과: {result}\n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
            color=discord.Color.green()
        ))

        # 타임아웃 취소
        if game.timeout_task:
            game.timeout_task.cancel()

async def show_hands(interaction: discord.Interaction, game, initial=False):
    player_hand = ' | '.join([f'{value}{suit}' for value, suit in game.player_hand])
    dealer_hand = ' | '.join([f'{value}{suit}' for value, suit in game.dealer_hand[:1]]) + " | ???" if initial else ' | '.join([f'{value}{suit}' for value, suit in game.dealer_hand])
    embed = discord.Embed(title="🃏 블랙잭 게임", color=discord.Color.green())
    embed.add_field(name=f"{game.user.display_name}의 손패", value=player_hand, inline=False)
    embed.add_field(name="🤖 딜러 손패", value=dealer_hand, inline=False)
    view = BlackjackView(game, interaction)

    if not interaction.response.is_done():
        await interaction.response.defer()

    try:
        await interaction.followup.send(embed=embed, view=view)
    except discord.errors.NotFound:
        await interaction.response.send_message(embed=embed, view=view)

# 슬롯머신 도움말 명령어
@bot.tree.command(name="슬롯머신도움", description="슬롯머신 게임의 사용 방법을 안내합니다.")
@app_commands.guild_only()
async def slot_machine_help(interaction: discord.Interaction):
    try:
        help_text = (
            "슬롯머신 게임 사용법:\n"
            "1. `/슬롯머신 <베팅 코인 수>`: 슬롯머신 게임을 시작합니다.\n"
            "2. 슬롯머신 결과에 따라 코인을 획득합니다.\n"
            "3. 같은 기호 2개가 나오면 2배의 코인을 획득합니다.\n"
            "4. 같은 기호 3개가 나오면 10배의 코인을 획득합니다.\n"
            "5. 7️⃣ 3개가 나오면 100배의 코인을 획득합니다.\n"
            "6. 당첨되지 않으면 베팅한 코인을 잃습니다."
        )
        embed = discord.Embed(
            title="슬롯머신 도움말",
            description=help_text,
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

@bot.tree.command(name="슬롯머신", description="슬롯머신 게임을 시작합니다.")
@app_commands.describe(bet="베팅할 코인 수")
@app_commands.guild_only()
async def slot_machine_command(interaction: discord.Interaction, bet: int):
    try:
        user_id = interaction.user.id
        if bet > get_user_coins(user_id):
            await interaction.response.send_message("베팅할 코인이 부족합니다.", ephemeral=True)
            return

        update_user_coins(user_id, -bet)
        emojis = ['🍒', '🍋', '🍊', '🍉', '7️⃣', '💰', '🎁', '🎈', '🐲', '💣', '⚽', '🏆']
        result = [random.choice(emojis) for _ in range(3)]
        result_str = ' | '.join(result)
        payout = 0
        net_coins = -bet
        is_jackpot = False
        is_super_jackpot = False

        if result[0] == result[1] == result[2] == '7️⃣':
            payout = bet * 100  # 7️⃣ 3개가 나오면 100배 지급
            is_super_jackpot = True
        elif result[0] == result[1] == result[2]:
            payout = bet * 10  # 잭팟: 같은 기호 3개가 나오면 10배 지급
            is_jackpot = True
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            payout = bet * 2

        update_user_coins(user_id, payout)
        net_coins += payout

        if payout > 0:
            update_slot_machine_stats(user_id, "승리", payout, bet)
        else:
            update_slot_machine_stats(user_id, "패배", 0, bet)

        embed = discord.Embed(
            title="슬롯머신 결과",
            description=f"🎰 슬롯머신 결과: {result_str} 🎰\n획득 코인: {format_coins(payout)}개 🪙\n현재 코인: {format_coins(get_user_coins(user_id))}개 🪙",
            color=discord.Color.green() if payout > 0 else discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

        if is_super_jackpot:
            super_jackpot_embed = discord.Embed(
                title="🎉 슈퍼 잭팟! 🎉",
                description=f"축하합니다! {interaction.user.mention}님이 슬롯머신에서 슈퍼 잭팟을 터뜨렸습니다! 💰\n획득 코인: {format_coins(payout)}개 🪙",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=super_jackpot_embed)
        elif is_jackpot:
            jackpot_embed = discord.Embed(
                title="🎉 잭팟! 🎉",
                description=f"축하합니다! {interaction.user.mention}님이 슬롯머신에서 잭팟을 터뜨렸습니다! 💰\n획득 코인: {format_coins(payout)}개 🪙",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=jackpot_embed)

    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

@bot.tree.command(name="홀짝", description="홀짝 게임을 시작합니다.")
@app_commands.describe(bet="베팅할 코인 수", choice="홀 또는 짝을 선택하세요")
@app_commands.choices(choice=[
    app_commands.Choice(name="홀", value="홀"),
    app_commands.Choice(name="짝", value="짝")
])
@app_commands.guild_only()
async def odd_even_command(interaction: discord.Interaction, bet: int, choice: app_commands.Choice[str]):
    try:
        user_id = interaction.user.id
        if bet > get_user_coins(user_id):
            await interaction.response.send_message("배팅할 코인이 부족합니다.", ephemeral=True)
            return
        
        update_user_coins(user_id, -bet)
        result = random.choice(["홀", "짝"])
        net_coins = 0

        if result == choice.value:
            net_coins = int(bet * 0.5)  # 승리 시 50% 추가
            update_user_coins(user_id, net_coins + bet)
            description = f"축하합니다! {result}을(를) 맞췄습니다. 획득 코인: {net_coins} 🪙"
            outcome = "승리"
        else:
            description = f"아쉽게도 틀렸습니다. 나왔던 결과: {result}\n손해 코인: {bet} 🪙"
            outcome = "패배"
            net_coins = -bet

        update_odd_even_stats(user_id, outcome, bet)

        await interaction.response.send_message(
            embed=discord.Embed(
                title="홀짝 게임 결과",
                description=f"{interaction.user.mention} {description}\n현재 코인: {format_coins(get_user_coins(user_id))}개 🪙",
                color=discord.Color.green() if outcome == "승리" else discord.Color.red()
            )
        )
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

# 업데이트 명령어
@bot.tree.command(name="업데이트", description="봇의 최신 업데이트 내용을 알려줍니다.")
@app_commands.guild_only()
async def update_command(interaction: discord.Interaction):
    try:
        if not os.path.exists('updates.json'):
            await interaction.response.send_message("업데이트 내용 파일을 찾을 수 없습니다.", ephemeral=True)
            return

        with open('updates.json', 'r', encoding='utf-8') as file:
            updates = json.load(file)

        total_updates = len(updates)
        if total_updates == 0:
            await interaction.response.send_message("등록된 업데이트 내용이 없습니다.", ephemeral=True)
            return

        # 첫 번째 페이지 보여주기
        await interaction.response.defer(ephemeral=True)
        await show_update_page(interaction, updates, 1)
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

async def show_update_page(interaction, updates, page):
    updates_per_page = 3
    total_updates = len(updates)
    total_pages = (total_updates + updates_per_page - 1) // updates_per_page

    start = (page - 1) * updates_per_page
    end = start + updates_per_page
    page_updates = updates[start:end]

    embed = discord.Embed(title="📢 봇 업데이트 내용", color=discord.Color.blue())
    for update in page_updates:
        details = "\n".join(update['details'])
        embed.add_field(
            name=f"{update['version']} - {update['date']}",
            value=f"{details}\n{'-'*30}",
            inline=False
        )

    view = UpdateView(page, total_pages, updates)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class UpdateView(discord.ui.View):
    def __init__(self, current_page, total_pages, updates):
        super().__init__()
        self.current_page = current_page
        self.total_pages = total_pages
        self.updates = updates

        if current_page > 1:
            self.add_item(UpdateButton("이전", "prev"))
        if current_page < total_pages:
            self.add_item(UpdateButton("다음", "next"))

class UpdateButton(discord.ui.Button):
    def __init__(self, label, direction):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        view: UpdateView = self.view
        if self.direction == "prev":
            view.current_page -= 1
        else:
            view.current_page += 1
        await show_update_page(interaction, view.updates, view.current_page)

# 코인 송금 명령어
@bot.tree.command(name="송금", description="다른 사용자에게 코인을 송금합니다.")
@app_commands.describe(받는사람="코인을 받을 사용자", 금액="송금할 코인 금액")
@app_commands.guild_only()
async def transfer_coins(interaction: discord.Interaction, 받는사람: discord.Member, 금액: int):
    try:
        sender_id = interaction.user.id
        receiver_id = 받는사람.id

        if 금액 <= 0:
            await interaction.response.send_message("송금할 금액은 0보다 커야 합니다.", ephemeral=True)
            return

        sender_coins = get_user_coins(sender_id)
        if 금액 > sender_coins:
            await interaction.response.send_message("송금할 코인이 부족합니다.", ephemeral=True)
            return

        update_user_coins(sender_id, -금액)
        update_user_coins(receiver_id, 금액)

        await interaction.response.send_message(
            embed=discord.Embed(
                title="코인 송금 완료",
                description=(
                    f"{interaction.user.mention}님이 {받는사람.mention}님에게 {format_coins(금액)}개 🪙 코인을 송금했습니다.\n"
                    f"내 현재 코인: {format_coins(get_user_coins(sender_id))}개 🪙\n"
                    f"{받는사람.display_name}의 현재 코인: {format_coins(get_user_coins(receiver_id))}개 🪙"
                ),
                color=discord.Color.green()
            )
        )
    except Exception as e:
        await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

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
    # 타이머가 이미 실행 중이라면 실행하지 않음
    if bot.disconnect_timer_active.get(interaction.guild.id):
        return

    bot.disconnect_timer_active[interaction.guild.id] = True  # 타이머 활성화 플래그 설정
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
    bot.disconnect_timer_active[interaction.guild.id] = False



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

        # 반복 재생 모드가 꺼져 있을 때만 재생 메시지 출력
        if not bot.repeat_mode.get(guild_id, False):
            # 재생 중인 노래를 메시지로 표시
            embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
            if player.thumbnail:
                embed.set_thumbnail(url=player.thumbnail)

            # 상호작용에 대한 응답이 완료되었는지 확인
            if interaction.response.is_done():
                playing_message = await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                playing_message = await interaction.response.send_message(embed=embed, ephemeral=True)

            # 재생 메시지를 봇이 관리
            bot.playing_messages[guild_id] = playing_message

    # 노래가 끝나면 자동 퇴장 타이머 실행
    if not bot.song_queues[guild_id]:
        await auto_disconnect_timer(voice_client, interaction)


async def auto_disconnect_timer(voice_client, interaction):
    timer = 300  # 5분 (300초)
    await asyncio.sleep(timer)

    # 자동 퇴장 타이머 함수
async def auto_disconnect_timer(voice_client, interaction):
    timer = 300  # 5분 (300초)
    await asyncio.sleep(timer)

    # 봇이 여전히 음성 채널에 있고, 노래를 재생하지 않으면 자동 퇴장
    if voice_client.is_connected() and (not voice_client.is_playing() or len(voice_client.channel.members) == 1):
        await voice_client.disconnect()

        # 임베드 메시지 생성
        embed = discord.Embed(title="자동 퇴장", description="5분간 실행된 작업이 없어 음성 채널에서 퇴장했어요!", color=discord.Color.red())
        await interaction.channel.send(embed=embed)
    else:
        # 디버깅용 로그
        print("봇이 아직 음성 채널에 있으며, 멤버 수는:", len(voice_client.channel.members))

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
    ensure_check_in_net_coins_column()
    updates_file = 'updates.json'
    if not validate_updates_json(updates_file):
        print(f"업데이트 JSON 파일 ({updates_file})의 무결성 검사가 실패했습니다. 파일을 확인하세요.")
        await bot.close()
        return

    await bot.tree.sync()
    await bot.change_presence(activity=discord.Game(name="명령어 도움은 /도움말"))
    monitor_system.start()
    print(f'지금부터 서버 관리를 시작합니다! 봇 {bot.user}')
    await asyncio.sleep(1800)  # 60초 대기 후 주가 변동 시작
    update_stock_prices.start()  # 봇 시작 시 주식 업데이트 루프 실행

# 봇 실행
bot.run(TOKEN)
