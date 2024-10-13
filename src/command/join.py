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

def join(bot):
    @bot.tree.command(name="입장", description="봇을 음성 채널로 호출합니다.")
    async def join(interaction: discord.Interaction):
        # 사용자가 음성 채널에 있는지 확인
        if not interaction.user.voice:
            await interaction.response.send_message(embed=discord.Embed(description="먼저 음성 채널에 들어가 주세요!", color=discord.Color.red()), ephemeral=True)
            return
    
        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client

        if voice_client is None:
        # 봇이 아직 음성 채널에 없으면, 사용자가 있는 채널로 연결
            await channel.connect()
            await interaction.response.send_message(embed=discord.Embed(description=f"'{channel.name}' 채널에 입장했습니다."), ephemeral=True)
        elif voice_client.channel != channel:
        # 봇이 다른 음성 채널에 있을 경우
            await interaction.response.send_message(embed=discord.Embed(description="현재 다른 통화방에서 노래를 재생 중이예요!", color=discord.Color.red()), ephemeral=True)
        else:
        # 봇이 이미 해당 채널에 있는 경우
            await interaction.response.send_message(embed=discord.Embed(description="봇이 이미 음성 채널에 있습니다."), ephemeral=True)