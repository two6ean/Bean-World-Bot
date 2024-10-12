import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.coin_setup import format_coins
from src.database.coin_management import get_user_coins, update_user_coins
from src.config.config import ADMIN_ROLE_ID


def manage_coins(bot):
    @bot.tree.command(name="코인관리", description="사용자에게 코인을 지급하거나 차감합니다.")
    @app_commands.choices(옵션=[
        app_commands.Choice(name="지급", value="지급"),
        app_commands.Choice(name="차감", value="차감")
    ])
    @app_commands.describe(옵션="지급 또는 차감을 선택하세요.", 사용자="대상 사용자", 금액="금액을 입력하세요.")
    @app_commands.guild_only()
    async def manage_coins(interaction: discord.Interaction, 옵션: app_commands.Choice[str], 사용자: discord.Member, 금액: int):
        try:
            if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
                await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
                return

            if 금액 <= 0:
                await interaction.response.send_message("금액은 0보다 커야 합니다.", ephemeral=True)
                return

            user_id = 사용자.id
            current_coins = get_user_coins(user_id)

            if 옵션.value == "지급":
                new_coins = current_coins + 금액
                action = "지급"
            else:
                if 금액 > current_coins:
                    await interaction.response.send_message("사용자의 코인이 부족합니다.", ephemeral=True)
                    return
                new_coins = current_coins - 금액
                action = "차감"

            if current_coins == 0 and 옵션.value == "차감":
                await interaction.response.send_message("사용자의 코인이 부족합니다.", ephemeral=True)
                return
        
            update_user_coins(user_id, 금액 if 옵션.value == "지급" else -금액)

            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"코인 {action} 완료",
                    description=(
                        f"{사용자.mention}님에게 {format_coins(금액)}개 🪙 코인을 {action}했습니다.\n"
                        f"현재 {사용자.display_name}의 코인: {format_coins(new_coins)}개 🪙"
                    ),
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)