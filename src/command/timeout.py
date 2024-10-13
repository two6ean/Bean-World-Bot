import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from src.config.config import ADMIN_ROLE_ID

# 타임아웃 명령어
def timeout(bot):
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