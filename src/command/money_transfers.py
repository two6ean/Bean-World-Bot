import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.coin_setup import format_coins
from src.database.coin_management import get_user_coins, update_user_coins

# 코인 송금 명령어
def money_transfers(bot):
    @bot.tree.command(name="송금", description="다른 사용자에게 코인을 송금합니다.")
    @app_commands.describe(받는사람="코인을 받을 사용자", 금액="송금할 코인 금액")
    @app_commands.guild_only()
    async def transfer_coins(interaction: discord.Interaction, 받는사람: discord.Member, 금액: int):
        try:
            sender_id = interaction.user.id
            receiver_id = 받는사람.id

            if 금액 <= 0:
                await interaction.response.send_message("송금할 금액은 0보다 커야 합니다.", ephemeral=True)
                return

            sender_coins = get_user_coins(sender_id)
            if 금액 > sender_coins:
                await interaction.response.send_message("송금할 코인이 부족합니다.", ephemeral=True)
                return

            update_user_coins(sender_id, -금액)
            update_user_coins(receiver_id, 금액)

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="코인 송금 완료",
                    description=(
                        f"{interaction.user.mention}님이 {받는사람.mention}님에게 {format_coins(금액)}개 🪙 코인을 송금했습니다.\n"
                        f"내 현재 코인: {format_coins(get_user_coins(sender_id))}개 🪙\n"
                        f"{받는사람.display_name}의 현재 코인: {format_coins(get_user_coins(receiver_id))}개 🪙"
                    ),
                    color=discord.Color.green()
                )
            )
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)