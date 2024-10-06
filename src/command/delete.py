import asyncio
import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.config import ADMIN_ROLE_ID

# 삭제 명령어
def delete(bot):
    @bot.tree.command(name="삭제", description="현재 채널의 모든 메시지를 삭제합니다.")
    @app_commands.guild_only()
    async def clear_channel(interaction: discord.Interaction):
        try:
            if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
                await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
                return

        # 먼저 인터랙션에 응답을 보냅니다.
            await interaction.response.send_message("메시지를 삭제하는 중입니다...", ephemeral=True)

            def check(msg):
                return True

            deleted = 0
            while True:
                deleted_msgs = await interaction.channel.purge(limit=50, check=check)
                deleted += len(deleted_msgs)
                if len(deleted_msgs) < 50:
                    break
                await asyncio.sleep(1)  # 각 배치 삭제 후 1초 대기

            await interaction.followup.send(f"{deleted}개의 메시지가 삭제되었습니다.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)