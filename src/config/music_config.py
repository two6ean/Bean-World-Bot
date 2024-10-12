import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import yt_dlp as youtube_dl
import ytdl
import ffmpeg
import nacl
from src.config.ytdl import ffmpeg_options, ytdl_format_options

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

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.thumbnail = data.get('thumbnail')
        self.source = source  # 추가된 라인

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

async def search_youtube(query):
    ytdl_search_options = ytdl_format_options.copy()
    ytdl_search_options['default_search'] = 'ytsearch'
    ytdl_search = youtube_dl.YoutubeDL(ytdl_search_options)
    search_result = ytdl_search.extract_info(query, download=False)
    if 'entries' in search_result:
        return search_result['entries'][0]['webpage_url']
    return None

# 자동 퇴장 타이머 함수 (중복 방지 및 재생 중 타이머 실행 방지)
async def auto_disconnect_timer(voice_client, interaction):
    guild_id = interaction.guild.id

    # 타이머가 이미 실행 중이라면 실행하지 않음
    if bot.disconnect_timer_active.get(guild_id):
        return

    bot.disconnect_timer_active[guild_id] = True  # 타이머 활성화 플래그 설정
    timer = 300  # 5분 (300초)
    await asyncio.sleep(timer)

    # 봇이 여전히 음성 채널에 있고, 노래를 재생하지 않거나 혼자 남았을 때 자동 퇴장
    if voice_client.is_connected() and (not voice_client.is_playing() or len(voice_client.channel.members) == 1):
        await voice_client.disconnect()

        # 퇴장 후 임베드 메시지 생성 및 전송
        embed = discord.Embed(
            title="자동 퇴장",
            description="5분 동안 아무 작업도 없어 음성 채널에서 퇴장했습니다!",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)

    # 타이머 종료 시 플래그 해제
    bot.disconnect_timer_active[guild_id] = False

async def play_next_song(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    guild_id = interaction.guild.id

    # 재생 목록이 없으면 타이머 시작
    if not bot.song_queues.get(guild_id):
        await auto_disconnect_timer(voice_client, interaction)  # 타이머 호출
        return

    # 현재 재생 중이거나 일시정지 상태일 때는 다음 곡을 재생하지 않음
    if voice_client.is_playing() or voice_client.is_paused():
        return

    # 큐에서 다음 곡을 꺼내서 재생
    if bot.song_queues[guild_id]:
        next_song = bot.song_queues[guild_id].pop(0)  # 큐에서 곡 제거
        player = await YTDLSource.from_url(next_song['url'], loop=bot.loop, stream=True)  # 다음 곡 불러오기

        # 반복 재생 모드가 켜져 있으면, 현재 곡을 큐에 다시 추가
        if bot.repeat_mode.get(guild_id, False):
            bot.song_queues[guild_id].insert(0, next_song)

        # 현재 재생 중인 곡 정보를 저장
        bot.currently_playing[guild_id] = {
            'title': player.title,
            'url': next_song['url'],
            'thumbnail': next_song['thumbnail']
        }

        # 플레이어 실행 및 다음 곡 재생 준비
        voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next_song(interaction), bot.loop).result())

        # 재생 중인 노래를 메시지로 표시
        embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
        if player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)

        try:
            # 상호작용에 대한 응답이 완료되었는지 확인 후 메시지 전송
            if interaction.response.is_done():
                playing_message = await interaction.followup.send(embed=embed)
            else:
                playing_message = await interaction.response.send_message(embed=embed)
            
            # 재생 메시지를 봇이 관리
            bot.playing_messages[guild_id] = playing_message
        except Exception as e:
            print(f"재생 메시지 전송 중 오류: {str(e)}")

    # 노래가 끝나면 자동 퇴장 타이머 실행
    if not bot.song_queues[guild_id]:
        await auto_disconnect_timer(voice_client, interaction)

async def play_specific_song(interaction: discord.Interaction, url: str):
    voice_client = interaction.guild.voice_client
    try:
        player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
        voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(clear_playing_message(interaction.guild.id), bot.loop).result())
        
        embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
        
        if player.thumbnail:
            embed.set_thumbnail(url=player.thumbnail)
        
        playing_message = await interaction.followup.send(embed=embed)
        bot.playing_messages[interaction.guild.id] = playing_message
    
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=f"오류 발생: {str(e)}", color=discord.Color.red()), ephemeral=True)

async def play_all_songs(interaction: discord.Interaction, urls: list):
    voice_client = interaction.guild.voice_client
    try:
        for url in urls:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(clear_playing_message(interaction.guild.id), bot.loop).result())
            embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
            playing_message = await interaction.followup.send(embed=embed)
            bot.playing_messages[interaction.guild.id] = playing_message
            await asyncio.sleep(player.data['duration'])  # 노래 길이만큼 대기
    except Exception as e:
        await interaction.followup.send(embed=discord.Embed(description=f"오류 발생: {str(e)}", color=discord.Color.red()), ephemeral=True)

async def clear_playing_message(guild_id):
    if guild_id in bot.playing_messages:
        message = bot.playing_messages[guild_id]
        try:
            await message.delete()
        except discord.NotFound:
            pass
        del bot.playing_messages[guild_id]

print(nacl.__version__)