import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

bot.playing_messages = {}
# 재생 중인 곡을 저장할 변수 추가
bot.currently_playing = {}
# 봇 초기화 시 타이머 플래그도 초기화
bot.disconnect_timer_active = {}
# 서버별 반복 재생 여부를 저장할 변수 추가
bot.repeat_mode = {}
# 서버별 재생 목록을 저장할 큐
bot.song_queues = {}
bot.playing_messages = {}

# 재생목록 명령어 (보기, 삭제) 수정
def playlist(bot):
    @bot.tree.command(name="재생목록", description="재생목록을 관리합니다.")
    @app_commands.describe(index="삭제할 곡의 번호(삭제 옵션일 경우)")
    @app_commands.choices(option=[
        app_commands.Choice(name="보기", value="보기"),
        app_commands.Choice(name="삭제", value="삭제")
    ])
    async def playlist(interaction: discord.Interaction, option: app_commands.Choice[str], index: int = None):
        guild_id = interaction.guild.id

    # 해당 서버에 재생목록이 없다면 생성
        if guild_id not in bot.song_queues:
            bot.song_queues[guild_id] = []

    # "보기" 옵션: 현재 재생목록 확인
        if option.value == "보기":
            if len(bot.song_queues[guild_id]) == 0 and guild_id not in bot.currently_playing:
                await interaction.response.send_message(embed=discord.Embed(description="현재 재생목록이 비어 있습니다.", color=discord.Color.blue()), ephemeral=True)
            else:
                embed = discord.Embed(title="현재 재생목록", color=discord.Color.green())

            # 현재 재생 중인 곡 표시
                if guild_id in bot.currently_playing:
                    current_song = bot.currently_playing[guild_id]
                    embed.add_field(name="▶️ 현재 재생 중:", value=f"**{current_song['title']}**", inline=False)

            # 대기 중인 곡 목록 표시
                for i, song in enumerate(bot.song_queues[guild_id], start=1):
                    embed.add_field(name=f"{i}.", value=song['title'], inline=False)

                await interaction.response.send_message(embed=embed, ephemeral=True)

    # "삭제" 옵션: 특정 곡 삭제
        elif option.value == "삭제":
            if len(bot.song_queues[guild_id]) == 0:
                await interaction.response.send_message(embed=discord.Embed(description="재생목록이 비어 있어 삭제할 곡이 없습니다.", color=discord.Color.red()), ephemeral=True)
            elif index is None or index < 1 or index > len(bot.song_queues[guild_id]):
                await interaction.response.send_message(embed=discord.Embed(description="올바른 곡 번호를 입력해주세요.", color=discord.Color.red()), ephemeral=True)
            else:
                removed_song = bot.song_queues[guild_id].pop(index - 1)  # 곡 삭제
                await interaction.response.send_message(embed=discord.Embed(description=f"**{removed_song['title']}** 곡을 재생목록에서 삭제했습니다.", color=discord.Color.green()), ephemeral=True)