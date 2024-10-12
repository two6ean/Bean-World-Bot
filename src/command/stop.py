import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.music_config import clear_playing_message

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

def stop(bot):
    @bot.tree.command(name="정지", description="음악을 정지합니다.")
    async def stop(interaction: discord.Interaction):
        voice_client = interaction.guild.voice_client
        guild_id = interaction.guild.id

        if not voice_client or not voice_client.is_connected():
            await interaction.response.send_message(embed=discord.Embed(description="봇이 음성 채널에 연결되어 있지 않습니다.", color=discord.Color.red()), ephemeral=True)
            return

        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()

        # 반복 재생 모드 해제
            bot.repeat_mode[guild_id] = False

        # 재생 중인 메시지 클리어
            await clear_playing_message(guild_id)

            await interaction.response.send_message(embed=discord.Embed(description="음악이 정지되었습니다. 반복 재생 모드가 해제되었습니다.", color=discord.Color.red()), ephemeral=True)
        else:
            await interaction.response.send_message(embed=discord.Embed(description="현재 재생 중인 음악이 없습니다.", color=discord.Color.red()), ephemeral=True)