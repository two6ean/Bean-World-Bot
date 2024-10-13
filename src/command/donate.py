import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands

# 도움말 명령어
class DonateView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="🔍도움말", url="https://happy-burn-b3c.notion.site/Bean-World-Bot-Wiki-9510929dacea47688691cfe3cbae8afe"))


def donate(bot):
    @bot.tree.command(name="도움말", description="명령어 사용을 도와줍니다.")
    @app_commands.guild_only()
    async def donate_command(interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="도움말",
                description=(
                    "Bean World Bot 명령어를 몰라서 불편함을 느끼셨나요?\n"
                    "그래서 준비했습니다! 도! 움! 말!\n\n"
                    "**사용방법**\n\n"
                    "아래의 버튼을 클릭해 도움말 웹사이트로 이동해보세요!\n\n"
                    "앞으로도 유저분들을 위한 Bean World가 되겠습니다! 감사합니다!"
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=DonateView(), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

