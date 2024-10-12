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

# 매도 명령어
def sell_stocks(bot):
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