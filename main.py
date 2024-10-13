import discord
from discord.ext import commands, tasks
import os
import discord.utils
import asyncio
import yt_dlp as youtube_dl
import sys

from src.config.config import TOKEN, USER_IDS
from src.database.db import get_cursor, get_connection
from src.config.ytdl import ytdl_format_options
from src.config.coin_setup import ensure_check_in_net_coins_column
from src.config.stock_class import update_stock_prices
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
from src.command.slot import slot
from src.command.odd_even import odd_even
from src.command.update import update, validate_updates_json
from src.command.money_transfers import money_transfers
from src.command.manage_coins import manage_coins
from src.command.money_making import money_making
from src.command.my_coins import my_coins
from src.command.coin_ranking import coin_ranking
from src.command.rps import rps
from src.command.show_stocks import show_stocks
from src.command.buy_stocks import buy_stocks
from src.command.sell_stocks import sell_stocks
from src.command.show_portfolio import show_portfolio
from src.command.system import system
from src.command.my_stats import my_stats
from src.event.monitoring_system import monitor_system
from src.command.donate import donate
from src.command.join import join
from src.command.leave import leave
from src.command.play import play
from src.command.stop import stop
from src.command.playlist import playlist
from src.command.pause import pause
from src.command.repeat import repeat
from src.command.resume import resume
from src.command.skip import skip

c = get_cursor()
conn = get_connection()

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

youtube_dl.utils.bug_reports_message = lambda: ''

bot.playing_messages = {}
# 재생 중인 곡을 저장할 변수 추가
bot.currently_playing = {}
# 봇 초기화 시 타이머 플래그도 초기화
bot.disconnect_timer_active = {}
# 서버별 반복 재생 여부를 저장할 변수 추가
bot.repeat_mode = {}
# 서버별 재생 목록을 저장할 큐
bot.song_queues = {}
bot.playing_messages = {}

# 메시지 검사 및 타임아웃 처리
@bot.event
async def on_message(message):
    await handle_message(message, bot)
    await bot.process_commands(message)

@tasks.loop(minutes=10)
async def monitor_system_task():
    await monitor_system(bot, USER_IDS)

@monitor_system_task.before_loop
async def before_monitor_system():
    await bot.wait_until_ready()

# 봇 준비
@bot.event
async def on_ready():
    try:
        print(f'지금부터 서버 관리를 시작합니다! 봇 {bot.user}')
        
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
        blackjack(bot)
        odd_even(bot)
        update(bot)
        money_transfers(bot)
        delete(bot)
        slot(bot)
        help_slot(bot)
        manage_coins(bot)
        money_making(bot)
        my_coins(bot)
        coin_ranking(bot)
        rps(bot)
        show_stocks(bot)
        buy_stocks(bot)
        sell_stocks(bot)
        show_portfolio(bot)
        system(bot)
        my_stats(bot)
        donate(bot)
        join(bot)
        leave(bot)
        play(bot)
        stop(bot)
        playlist(bot)
        pause(bot)
        repeat(bot)
        resume(bot)
        skip(bot)

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
        print(f'{len(synced)}개의 명령어가 동기화되었습니다.')
    except Exception as e:
        print(f'명령어 동기화 중 오류 발생: {e}')

        # 봇의 현재 상태 메시지 설정
        await bot.change_presence(activity=discord.Game(name="명령어 도움은 /도움말"))

        # 시스템 모니터링 시작
        monitor_system_task.start()

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
