import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.config import ANNOUNCEMENT_CHANNEL_ID

#공지
def announcement(bot):
    @bot.tree.command(name="공지", description="공지사항을 전송합니다.")
    @app_commands.describe(메시지="전송할 공지 내용을 입력하세요.", 역할들="멘션할 역할을 공백으로 구분하여 입력하세요.")
    @app_commands.guild_only()
    async def announce_command(interaction: discord.Interaction, 메시지: str, 역할들: str = ""):
        try:
            channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
            if channel is None:
                await interaction.response.send_message("공지 채널을 찾을 수 없습니다. 채널 ID를 확인하세요.", ephemeral=True)
                return
        
            role_mentions = []
            if 역할들:
                role_ids = 역할들.split()
                guild = interaction.guild
                for role_id in role_ids:
                    role_id = role_id.strip('<@&>')
                    if role_id.isdigit():
                        role = guild.get_role(int(role_id))
                        if role:
                            role_mentions.append(f"||{role.mention}||")
                        else:
                            await interaction.response.send_message(f"역할 ID '{role_id}'을(를) 찾을 수 없습니다.", ephemeral=True)
                            return
        
            role_mentions_text = ' '.join(role_mentions) if role_mentions else ""
        
            embed = discord.Embed(
                title="📢 공지사항",
                description=메시지,
                color=discord.Color.gold()
            )
            embed.set_footer(text=f"작성자: {interaction.user.name}", icon_url=interaction.user.avatar.url)
        
            await channel.send(content=role_mentions_text, embed=embed)
            await interaction.response.send_message("공지가 전송되었습니다.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)