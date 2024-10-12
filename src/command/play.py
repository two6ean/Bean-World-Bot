import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp as youtube_dl
from src.config.music_config import search_youtube, play_next_song
from src.config.ytdl import ytdl_format_options  # ytdl_format_options는 올바르게 설정되어 있다고 가정

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

youtube_dl.utils.bug_reports_message = lambda: ''

# yt_dlp로 유튜브 다운로드를 위한 설정
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

def play(bot):
    @bot.tree.command(name="재생", description="유튜브 URL의 음악을 재생합니다.")
    @app_commands.describe(url_or_search="재생할 유튜브 URL 또는 검색어")
    async def play(interaction: discord.Interaction, url_or_search: str):
        voice_client = interaction.guild.voice_client
        if not interaction.user.voice:
            await interaction.response.send_message(embed=discord.Embed(description="먼저 음성 채널에 연결되어야 합니다.", color=discord.Color.red()), ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if not voice_client or not voice_client.is_connected():
            await channel.connect()

        voice_client = interaction.guild.voice_client

        await interaction.response.defer(ephemeral=True)

        loop = asyncio.get_event_loop()

        try:
            # URL 또는 검색어 처리
            if not url_or_search.startswith("http"):
                url_or_search = await search_youtube(url_or_search)  # 검색어를 URL로 변환
        
            # URL이 있는 경우에만 추출 시도
            info = await loop.run_in_executor(None, lambda: ytdl.extract_info(url_or_search, download=False))
            title = info.get('title', '제목 없음')
            url = info.get('webpage_url')
            thumbnail = info.get('thumbnail')

            # 재생 목록에 추가
            guild_id = interaction.guild.id
            if guild_id not in bot.song_queues:
                bot.song_queues[guild_id] = []

            bot.song_queues[guild_id].append({'title': title, 'url': url, 'thumbnail': thumbnail})

            # 현재 곡이 재생 중이지 않다면 바로 재생 시작
            if not voice_client.is_playing() and not voice_client.is_paused():
                await play_next_song(interaction)
            else:
                await interaction.followup.send(embed=discord.Embed(description=f"**{title}**이(가) 재생 목록에 추가되었습니다.", color=discord.Color.blue()), ephemeral=True)

        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(description=f"오류 발생: {str(e)}", color=discord.Color.red()), ephemeral=True)