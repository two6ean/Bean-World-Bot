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

def repeat(bot):
    @bot.tree.command(name="반복재생", description="현재 재생 중인 곡을 반복 재생합니다.")
    @app_commands.describe(option="반복 여부 설정 (켜기/끄기)")
    @app_commands.choices(option=[
        app_commands.Choice(name="켜기", value="켜기"),
        app_commands.Choice(name="끄기", value="끄기")
    ])
    async def repeat(interaction: discord.Interaction, option: app_commands.Choice[str]):
        guild_id = interaction.guild.id

        if option.value == "켜기":
            bot.repeat_mode[guild_id] = True
        
        # 현재 재생 중인 곡이 있으면 그 곡을 큐에 추가
            if guild_id in bot.currently_playing:
                current_song = bot.currently_playing[guild_id]
                bot.song_queues[guild_id].insert(0, current_song)

            await interaction.response.send_message(embed=discord.Embed(description="반복 재생이 **켜졌습니다**.", color=discord.Color.green()), ephemeral=True)

        elif option.value == "끄기":
            bot.repeat_mode[guild_id] = False

        # 반복 모드를 끌 때, 큐에 현재 곡이 있는지 확인 후 제거
            if guild_id in bot.song_queues and bot.currently_playing.get(guild_id) in bot.song_queues[guild_id]:
                bot.song_queues[guild_id].remove(bot.currently_playing[guild_id])

            await interaction.response.send_message(embed=discord.Embed(description="반복 재생이 **꺼졌습니다**.", color=discord.Color.red()), ephemeral=True)