import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands

# 슬롯머신 도움말 명령어
def help_slot(bot):
    @bot.tree.command(name="슬롯머신도움", description="슬롯머신 게임의 사용 방법을 안내합니다.")
    @app_commands.guild_only()
    async def slot_machine_help(interaction: discord.Interaction):
        try:
            help_text = (
                "슬롯머신 게임 사용법:\n"
                "1. `/슬롯머신 <베팅 코인 수>`: 슬롯머신 게임을 시작합니다.\n"
                "2. 슬롯머신 결과에 따라 코인을 획득합니다.\n"
                "3. 같은 기호 2개가 나오면 2배의 코인을 획득합니다.\n"
                "4. 같은 기호 3개가 나오면 10배의 코인을 획득합니다.\n"
                "5. 7️⃣ 3개가 나오면 100배의 코인을 획득합니다.\n"
                "6. 당첨되지 않으면 베팅한 코인을 잃습니다."
            )
            embed = discord.Embed(
                title="슬롯머신 도움말",
                description=help_text,
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)