import random
import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.coin_management import get_user_coins, update_user_coins
from src.database.game_stats import update_odd_even_stats
from src.config.coin_setup import format_coins

#홀짝 게임 명령어
def odd_even(bot):
    @bot.tree.command(name="홀짝", description="홀짝 게임을 시작합니다.")
    @app_commands.describe(bet="베팅할 코인 수", choice="홀 또는 짝을 선택하세요")
    @app_commands.choices(choice=[
        app_commands.Choice(name="홀", value="홀"),
        app_commands.Choice(name="짝", value="짝")
    ])
    @app_commands.guild_only()
    async def odd_even_command(interaction: discord.Interaction, bet: int, choice: app_commands.Choice[str]):
        try:
            user_id = interaction.user.id
            if bet > get_user_coins(user_id):
                await interaction.response.send_message("배팅할 코인이 부족합니다.", ephemeral=True)
                return
        
            update_user_coins(user_id, -bet)
            result = random.choice(["홀", "짝"])
            net_coins = 0

            if result == choice.value:
                net_coins = int(bet * 0.5)  # 승리 시 50% 추가
                update_user_coins(user_id, net_coins + bet)
                description = f"축하합니다! {result}을(를) 맞췄습니다. 획득 코인: {net_coins} 🪙"
                outcome = "승리"
            else:
                description = f"아쉽게도 틀렸습니다. 나왔던 결과: {result}\n손해 코인: {bet} 🪙"
                outcome = "패배"
                net_coins = -bet

            update_odd_even_stats(user_id, outcome, bet)

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="홀짝 게임 결과",
                    description=f"{interaction.user.mention} {description}\n현재 코인: {format_coins(get_user_coins(user_id))}개 🪙",
                    color=discord.Color.green() if outcome == "승리" else discord.Color.red()
                )
            )
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)