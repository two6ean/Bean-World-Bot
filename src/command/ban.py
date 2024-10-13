import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.config import ADMIN_ROLE_ID

# 밴 명령어
def ban(bot):
    @bot.tree.command(name="밴", description="사용자를 차단합니다.")
    @app_commands.describe(사용자="차단할 사용자를 선택하세요.", 이유="차단 사유를 입력하세요.")
    @app_commands.guild_only()
    async def ban_command(interaction: discord.Interaction, 사용자: discord.Member, 이유: str = None):
        try:
            if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
                await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
                return

            try:
                await 사용자.ban(reason=이유)
            except discord.Forbidden:
                await interaction.response.send_message("사용자를 차단할 권한이 없습니다.", ephemeral=True)
                return
            except discord.HTTPException as e:
                await interaction.response.send_message(f"사용자 차단 중 오류가 발생했습니다: {str(e)}", ephemeral=True)
                return

            embed = discord.Embed(
                title="사용자 차단 알림",
                description=(
                    f"{사용자.mention}님이 서버에서 차단되었습니다."
                    + (f"\n이유: {이유}" if 이유 else "")
                ),
                color=discord.Color.red()
            )
            await interaction.channel.send(embed=embed)
            await interaction.response.send_message("사용자가 성공적으로 차단되었습니다.", ephemeral=True)
    
        except Exception as e:
            await interaction.response.send_message(f"예기치 못한 오류가 발생했습니다: {str(e)}", ephemeral=True)