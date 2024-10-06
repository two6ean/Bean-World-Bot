import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.hangang_api import Hangang

# 한강 API 데이터를 가져오기 위한 인스턴스 생성
hangang_api = Hangang()

# 한강 물 온도 정보를 가져옴
hangang_info = hangang_api.get_info()

def hangang(bot):
    @bot.tree.command(name="한강물온도", description="현재 한강 물 온도를 표시합니다. (음악 듣는 중에 사용해 보세요!)")
    @app_commands.guild_only()
    async def hangang_temp_command(interaction: discord.Interaction):
        try:
            hangang = hangang_api
            info = hangang_info

            if info['status'] == "ok":
                embed = discord.Embed(title="한강물 온도", color=discord.Color.blue())
                embed.add_field(name="한강", value=f"온도: {info['temp']} °C\n마지막 업데이트: {info['last_update']}\nPH: {info['ph']}", inline=False)
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(info['msg'], ephemeral=True)
        except Exception as e:
            print(f"명령어 처리 중 오류 발생: {e}")
            await interaction.response.send_message("명령어를 처리하는 중 오류가 발생했습니다.", ephemeral=True)