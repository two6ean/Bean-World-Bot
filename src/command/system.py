import discord
import psutil
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.config import ADMIN_ROLE_ID, USER_IDS

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

def system(bot):
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