import discord
from src.database.stock_db import load_stocks_from_db

# 봇 시작 시 주식 정보를 DB에서 불러옴
stocks = load_stocks_from_db()

players = {}

def show_stocks(bot):
    @bot.tree.command(name="주식목록", description="현재 주식 가격을 확인합니다.")
    async def show_stocks(interaction: discord.Interaction):
        stock_message = "```diff\n"

        for stock in stocks:
            if stock.is_listed:
                change = stock.price_change()  # 주식의 가격 변동량 계산

                if change > 0:
                    status = f"+ {stock.name}: 💰{int(stock.price)} ( ▲ {int(change)} )\n"
                elif change < 0:
                    status = f"- {stock.name}: 💰{int(stock.price)} ( ▼ {abs(int(change))} )\n"
                else:
                    status = f"  {stock.name}: 💰{int(stock.price)} ( ■ {int(change)} )\n"
            else:
                status = f"  {stock.name}: 💰{int(stock.price)} ( 상장폐지 )\n"

            stock_message += status

        stock_message += "```"

        embed = discord.Embed(title="📈 주식 목록", description=stock_message, color=discord.Color.blue())
        await interaction.response.send_message(embed=embed)