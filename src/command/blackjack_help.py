import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands

# 블랙잭 도움말 명령어
def blackjack_help(bot):
    @bot.tree.command(name="블랙잭도움", description="블랙잭 게임의 사용 방법을 안내합니다.")
    @app_commands.guild_only()
    async def blackjack_help(interaction: discord.Interaction):
        try:
            help_text = (
                "블랙잭 게임 사용법:\n"
                "1. `/블랙잭 <베팅 코인 수>`: 블랙잭 게임을 시작합니다.\n"
                "2. `카드추가`: 플레이어의 손에 카드를 추가합니다.\n"
                "3. `카드유지`: 더 이상 카드를 받지 않고 유지합니다.\n"
                "4. 딜러의 카드와 비교하여 21에 가까운 사람이 승리합니다.\n"
                "5. 승리 시 베팅 코인의 2배를 획득합니다.\n\n"
                "* J, Q, K는 10, A는 11의 숫자를 가지고 있습니다. *"
            )
            embed = discord.Embed(
                title="블랙잭 도움말",
                description=help_text,
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)