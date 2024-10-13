import discord
from discord.ext import commands
from discord import Embed
import asyncio
import yt_dlp as youtube_dl
import youtube_dl as ytdl
import ffmpeg
import nacl
from src.config.ytdl import ffmpeg_options, ytdl_format_options

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

# yt_dlp 설정
youtube_dl.utils.bug_reports_message = lambda: ''
ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('webpage_url')
        self.thumbnail = data.get('thumbnail')
        self.source = source

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
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

async def auto_disconnect_timer(bot, voice_client, text_channel, guild_id):
    if bot.disconnect_timer_active.get(guild_id):
        return

    bot.disconnect_timer_active[guild_id] = True  # 타이머 활성화 플래그 설정
    timer = 300  # 5분 (300초)
    await asyncio.sleep(timer)

    if voice_client.is_connected() and (not voice_client.is_playing() or len(voice_client.channel.members) == 1):
        await voice_client.disconnect()
        embed = discord.Embed(
            title="자동 퇴장",
            description="5분 동안 아무 작업도 없어 음성 채널에서 퇴장했습니다!",
            color=discord.Color.red()
        )
        await text_channel.send(embed=embed)

    bot.disconnect_timer_active[guild_id] = False

async def play_next_song(bot, guild_id, text_channel, deferred_message=None):
    voice_client = text_channel.guild.voice_client

    if not bot.song_queues.get(guild_id):
        await auto_disconnect_timer(bot, voice_client, text_channel, guild_id)
        return

    if voice_client.is_playing() or voice_client.is_paused():
        return

    if bot.song_queues[guild_id]:
        next_song = bot.song_queues[guild_id].pop(0)
        player = await YTDLSource.from_url(next_song['url'], loop=bot.loop, stream=True)

        # 곡이 반복 재생 모드인 경우, 현재 곡을 다시 큐에 삽입
        if bot.repeat_mode.get(guild_id, False):
            bot.song_queues[guild_id].insert(0, next_song)

        # 현재 곡 정보 업데이트
        bot.currently_playing[guild_id] = {
            'title': player.title,
            'url': next_song['url'],
            'thumbnail': next_song['thumbnail']
        }

        def after_playing(error):
            coro = play_next_song(bot, guild_id, text_channel)
            fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"오류 발생: {e}")

        voice_client.play(player, after=after_playing)

        # 현재 곡이 반복 재생 모드일 때는 새로운 재생 메시지를 출력하지 않음
        if not bot.repeat_mode.get(guild_id, False):
            embed = discord.Embed(title="재생 중", description=f'**{player.title}**', color=discord.Color.green())
            if player.thumbnail:
                embed.set_thumbnail(url=player.thumbnail)

            try:
                # Send the "Now playing" message
                playing_message = await text_channel.send(embed=embed)
                bot.playing_messages[guild_id] = playing_message

                # Delete the deferred message if it exists
                if deferred_message:
                    await deferred_message.delete()

            except Exception as e:
                print(f"재생 메시지 전송 중 오류: {str(e)}")

    if not bot.song_queues[guild_id]:
        await auto_disconnect_timer(bot, voice_client, text_channel, guild_id)

async def clear_playing_message(guild_id):
    if hasattr(bot, 'playing_messages') and guild_id in bot.playing_messages:
        message = bot.playing_messages[guild_id]
        try:
            await message.delete()
        except discord.NotFound:
            pass
        del bot.playing_messages[guild_id]