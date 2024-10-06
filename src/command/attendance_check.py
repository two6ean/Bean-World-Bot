import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from src.database.db import get_cursor, get_connection
from src.config.config import KST
from src.config.time_utils import get_korean_time
from src.database.coin_management import get_user_coins ,update_user_coins
from src.config.coin_setup import format_coins

c = get_cursor()
conn = get_connection()

# 출석 체크 명령어 
def attendance_check(bot):
    @bot.tree.command(name="출석체크", description="일일 출석 체크로 코인을 획득하고 기록을 남깁니다.")
    @app_commands.guild_only()
    async def check_in_command(interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            current_time = get_korean_time()

            # 사용자 출석 체크 정보 조회
            c.execute("SELECT check_in_count, last_check_in FROM attendance WHERE user_id = ?", (user_id,))
            row = c.fetchone()

            if row:
                check_in_count, last_check_in = row
                last_check_in_time = datetime.fromisoformat(last_check_in).astimezone(KST)
                time_diff = (current_time - last_check_in_time).total_seconds()
                if time_diff < 86400:
                    time_remaining = 86400 - time_diff
                    hours, remainder = divmod(time_remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="출석체크",
                            description=f"출석 체크는 24시간에 한 번만 가능합니다. 남은 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초",
                            color=discord.Color.red()
                        )
                    )
                    return

            # 출석 체크 횟수 업데이트 및 마지막 출석 시간 갱신
                check_in_count += 1
                c.execute("UPDATE attendance SET check_in_count = ?, last_check_in = ? WHERE user_id = ?", (check_in_count, current_time.isoformat(), user_id))
            else:
            # 새로운 사용자의 출석 체크 정보 삽입
                check_in_count = 1
                c.execute("INSERT INTO attendance (user_id, check_in_count, last_check_in) VALUES (?, ?, ?)", (user_id, check_in_count, current_time.isoformat()))

            conn.commit()

        # 코인 지급
            update_user_coins(user_id, 100)
            c.execute("UPDATE game_stats SET check_in_net_coins = check_in_net_coins + 100 WHERE user_id = ?", (user_id,))
            conn.commit()

            await interaction.response.send_message(
                embed=discord.Embed(
                    title="출석체크",
                    description=f"{interaction.user.mention} 출석체크 완료! 100 코인을 받았습니다. 현재 코인: {format_coins(get_user_coins(user_id))}개 🪙 \n현재까지 총 {check_in_count}회 출석체크를 했습니다.",
                    color=discord.Color.green()
                )
            )
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)