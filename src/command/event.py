import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from src.config.config import ADMIN_ROLE_ID
from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

# 이벤트 명령어 정의
def event(bot):
    @bot.tree.command(name="이벤트", description="이벤트를 관리합니다.")
    @app_commands.choices(옵션=[
        app_commands.Choice(name="목록", value="목록"),
        app_commands.Choice(name="등록", value="등록"),
        app_commands.Choice(name="삭제", value="삭제"),
        app_commands.Choice(name="참여", value="참여")
    ])
    @app_commands.describe(
        옵션="이벤트 관리 옵션을 선택하세요.",
        이름="이벤트 이름을 입력하세요.",
        일자="이벤트 일자를 입력하세요 (예: 2008-12-05 11:00).",
        종료기간="이벤트 종료 일자를 입력하세요 (예: 2008-12-06 11:00).",
        장소="이벤트 장소를 입력하세요."
    )
    @app_commands.guild_only()
    async def event_command(interaction: discord.Interaction, 옵션: app_commands.Choice[str], 이름: str = None, 일자: str = None, 종료기간: str = None, 장소: str = None):
        try:
            if 옵션.value in ["등록", "삭제"]:
                if ADMIN_ROLE_ID not in [role.id for role in interaction.user.roles]:
                    await interaction.response.send_message("이 명령어를 사용할 권한이 없습니다.", ephemeral=True)
                    return

            if 옵션.value == "등록" and 이름 and 일자 and 종료기간 and 장소:
                try:
                    event_date = datetime.strptime(일자, '%Y-%m-%d %H:%M')
                    end_date = datetime.strptime(종료기간, '%Y-%m-%d %H:%M')
                except ValueError:
                    await interaction.response.send_message("일자 형식이 잘못되었습니다. 올바른 형식: YYYY-MM-DD HH:MM", ephemeral=True)
                    return

                if event_date >= end_date:
                    await interaction.response.send_message("종료기간은 시작일자 이후여야 합니다.", ephemeral=True)
                    return

                c.execute("INSERT INTO events (name, date, end_date, location, participants) VALUES (?, ?, ?, ?, ?)", (이름, 일자, 종료기간, 장소, ""))
                conn.commit()
                await interaction.response.send_message(f"이벤트 '{이름}'이(가) {일자}에 {장소}에서 시작하며, 종료일은 {종료기간}입니다.", ephemeral=True)
            elif 옵션.value == "삭제" and 이름:
                c.execute("SELECT name FROM events WHERE name = ?", (이름,))
                if c.fetchone() is None:
                    await interaction.response.send_message(f"이벤트 '{이름}'가 존재하지 않습니다.", ephemeral=True)
                else:
                    c.execute("DELETE FROM events WHERE name = ?", (이름,))
                    conn.commit()
                    await interaction.response.send_message(f"이벤트 '{이름}'가 삭제되었습니다.", ephemeral=True)
            elif 옵션.value == "참여" and 이름:
                c.execute("SELECT participants FROM events WHERE name = ?", (이름,))
                row = c.fetchone()
                if row is None:
                    await interaction.response.send_message(f"이벤트 '{이름}'가 존재하지 않습니다.", ephemeral=True)
                else:
                    participants = row[0].split(',') if row[0] else []
                    if str(interaction.user.id) in participants:
                        await interaction.response.send_message(f"이미 이벤트 '{이름}'에 참여 중입니다.", ephemeral=True)
                    else:
                        participants.append(str(interaction.user.id))
                        c.execute("UPDATE events SET participants = ? WHERE name = ?", (','.join(participants), 이름))
                        conn.commit()
                        await interaction.response.send_message(f"이벤트 '{이름}'에 참여하였습니다.", ephemeral=True)
            elif 옵션.value == "목록":
                c.execute("SELECT name, date, end_date, location, participants FROM events")
                events = c.fetchall()
                now = datetime.now()

                if events:
                    embed = discord.Embed(title="이벤트 목록", color=discord.Color.blue())
                    for event in events:
                        event_date = datetime.strptime(event[1], '%Y-%m-%d %H:%M')
                        end_date = datetime.strptime(event[2], '%Y-%m-%d %H:%M')
                        if end_date > now:
                            participants_list = [interaction.guild.get_member(int(id)).mention for id in event[4].split(',') if id]
                            participants_text = ', '.join(participants_list) if participants_list else "없음"
                            embed.add_field(
                                name=event[0],
                                value=f"일자: {event[1]}\n종료기간: {event[2]}\n장소: {event[3]}\n참여자: {participants_text}",
                                inline=False
                            )
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("등록된 이벤트가 없습니다.", ephemeral=True)
            else:
                await interaction.response.send_message("잘못된 명령어 사용입니다. 사용법: /이벤트 목록, /이벤트 등록 <이름> <일자> <종료기간> <장소>, /이벤트 삭제 <이름>, /이벤트 참여 <이름>", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)
# 오래된 이벤트 삭제 작업
    @tasks.loop(hours=24)
    async def remove_past_events():
        now = datetime.now()
        c.execute("SELECT id, end_date FROM events")
        events = c.fetchall()

        for event in events:
            end_date = datetime.strptime(event[1], '%Y-%m-%d %H:%M')
            if end_date < now:
                c.execute("DELETE FROM events WHERE id = ?", (event[0],))
        conn.commit()