import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.coin_management import get_user_coins, update_user_coins
from src.config.coin_setup import format_coins

# 내코인 명령어
def my_coins(bot):
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