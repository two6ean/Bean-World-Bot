import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.coin_management import get_user_coins
from src.config.coin_setup import format_coins
from src.database.stock_db import load_stocks_from_db
from src.config.stock_class import get_or_create_player

# 봇 시작 시 주식 정보를 DB에서 불러옴
stocks = load_stocks_from_db()

player = {}

# 자산 조회 명령어
def show_portfolio(bot):
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