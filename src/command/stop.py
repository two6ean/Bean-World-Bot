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

def stop(bot):
    @bot.tree.command(name="정지", description="음악을 정지합니다.")
    async def stop(interaction: discord.Interaction):
        try:
            voice_client = interaction.guild.voice_client
            guild_id = interaction.guild.id

            # 상호작용 응답을 지연
            await interaction.response.defer(ephemeral=True)

            if not voice_client or not voice_client.is_connected():
                await interaction.followup.send(embed=discord.Embed(description="봇이 음성 채널에 연결되어 있지 않습니다.", color=discord.Color.red()))
                return

            # 재생 중이거나 일시정지 상태인 경우
            if voice_client.is_playing() or voice_client.is_paused():
                voice_client.stop()

                # 반복 재생 모드 해제
                bot.repeat_mode[guild_id] = False

                # 재생 중인 메시지 클리어 - guild_id 전달
                await clear_playing_message(guild_id)

                # 작업 완료 후 메시지 전송
                await interaction.followup.send(embed=discord.Embed(description="음악이 정지되었습니다. 반복 재생 모드가 해제되었습니다.", color=discord.Color.red()))
            else:
                # 현재 재생 중인 음악이 없을 때의 응답
                await interaction.followup.send(embed=discord.Embed(description="현재 재생 중인 음악이 없습니다.", color=discord.Color.red()))
        
        except Exception as e:
            await interaction.followup.send(embed=discord.Embed(description=f"오류가 발생했습니다: {str(e)}", color=discord.Color.red()))