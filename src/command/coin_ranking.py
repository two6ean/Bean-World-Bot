import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.coin_setup import format_coins
from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

def coin_ranking(bot):
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