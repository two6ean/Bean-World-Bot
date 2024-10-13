import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.db import get_cursor, get_connection
from src.config.config import ADMIN_ROLE_ID

c = get_cursor()
conn = get_connection()

# 금지 단어 관리 명령어
def banned_word(bot):
    @bot.tree.command(name="금지단어", description="금지된 단어를 관리합니다.")
    @app_commands.choices(옵션=[
        app_commands.Choice(name="추가", value="추가"),
        app_commands.Choice(name="삭제", value="삭제"),
        app_commands.Choice(name="리스트", value="리스트")
    ])
    @app_commands.describe(옵션="동작을 선택하세요 (추가, 삭제, 리스트).", 단어="금지할 단어를 입력하세요.")
    @app_commands.guild_only()
    async def ban_word_command(interaction: discord.Interaction, 옵션: app_commands.Choice[str], 단어: str = None):
        try:
            if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
                await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
                return
        
            if 옵션.value == "추가" and 단어:
                c.execute("INSERT INTO banned_words (word) VALUES (?)", (단어,))
                conn.commit()
                await interaction.response.send_message(f"금지된 단어 '{단어}'가 추가되었습니다.", ephemeral=True)
            elif 옵션.value == "삭제" and 단어:
                c.execute("SELECT word FROM banned_words WHERE word = ?", (단어,))
                if c.fetchone() is None:
                    await interaction.response.send_message(f"금지된 단어 '{단어}'가 데이터베이스에 없습니다.", ephemeral=True)
                else:
                    c.execute("DELETE FROM banned_words WHERE word = ?", (단어,))
                    conn.commit()
                    await interaction.response.send_message(f"금지된 단어 '{단어}'가 삭제되었습니다.", ephemeral=True)
            elif 옵션.value == "리스트":
                c.execute("SELECT word FROM banned_words")
                banned_words = [row[0] for row in c.fetchall()]
                if banned_words:
                    banned_words_text = " | ".join(banned_words)
                    embed = discord.Embed(title="금지된 단어 목록", description=banned_words_text, color=discord.Color.red())
                else:
                    embed = discord.Embed(title="금지된 단어 목록", description="등록된 금지된 단어가 없습니다.", color=discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("잘못된 명령어 사용입니다. 사용법: /밴단어 추가 <단어>, /밴단어 삭제 <단어>, /밴단어 리스트", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)