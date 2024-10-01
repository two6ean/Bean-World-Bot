import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands

# 후원 명령어
class DonateView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(discord.ui.Button(label="💻개발자 후원", url="https://buymeacoffee.com/ilbie"))
        
def sponsor(bot):
    @bot.tree.command(name="후원", description="후원 정보를 제공합니다.")
    @app_commands.guild_only()
    async def donate_command(interaction: discord.Interaction):
        try:
            embed = discord.Embed(
                title="후원 안내",
                description=(
                    "안녕하세요! 봇 개발 및 서버 운영을 위해 후원을 받고 있습니다.\n"
                    "후원해주시면 큰 도움이 됩니다!\n\n"
                    "**후원 방법:**\n\n"
                    "아래 버튼을 통해 후원해주시면 감사하겠습니다!\n\n"
                    "감사합니다! ;)"
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, view=DonateView(), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)