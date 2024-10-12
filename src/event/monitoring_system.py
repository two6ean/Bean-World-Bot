import discord
import psutil
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.command.system import calculate_network_usage
from src.config.config import USER_IDS

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

async def monitor_system(bot, USER_IDS):
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