import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from src.database.coin_management import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

def attendance_ranking(bot):
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