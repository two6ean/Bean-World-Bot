import discord
from datetime import timedelta
from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

async def handle_message(message, bot):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        return  # 개인 DM에서는 명령어를 처리하지 않음

    try:
        c.execute("SELECT word FROM banned_words")
        banned_words = [row[0] for row in c.fetchall()]

        for word in banned_words:
            if word in message.content:
                await message.delete()
                timeout_duration = timedelta(days=1)
                timeout_end = discord.utils.utcnow() + timeout_duration

                # 사용자에게 DM을 보내기
                try:
                    await message.author.send(
                        embed=discord.Embed(
                            title="타임아웃 알림",
                            description=(
                                "금지된 단어를 사용하여 1일(24시간) 동안 타임아웃 되었습니다.\n"
                                "오작동 또는 다른 문의가 있을 시 OWNER의 갠디로 문의해주세요."
                            ),
                            color=discord.Color.red()
                        )
                    )
                except discord.Forbidden:
                    print(f"사용자 {message.author}에게 DM을 보낼 수 없습니다.")

                # 타임아웃 적용
                try:
                    await message.author.edit(timed_out_until=timeout_end)
                except discord.Forbidden:
                    print(f"{message.author}에게 타임아웃을 적용할 수 없습니다.")
                    continue  # 타임아웃 적용에 실패하면 다음 금지된 단어로 넘어감

                # 해당 채널에 임베드 메시지 보내기 (사용자 멘션 포함)
                warning_embed = discord.Embed(
                    title="금지된 단어 사용",
                    description=(
                        f"{message.author.mention} 금지된 단어를 사용하여 1일(24시간) 동안 타임아웃 되었습니다."
                    ),
                    color=discord.Color.red()
                )
                warning_message = await message.channel.send(embed=warning_embed)
                
                # 일정 시간 후에 메시지 삭제
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=10))
                await warning_message.delete()

                break
    except Exception as e:
        print(f"오류 발생: {str(e)}")

# 명령어 처리 이후 메시지를 전파하기 위한 함수
async def process_commands(message, bot):
    await bot.process_commands(message)