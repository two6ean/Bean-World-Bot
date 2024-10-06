import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone, timedelta

# 핑 명령어
def ping(bot):
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