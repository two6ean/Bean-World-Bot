import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
import os
import json

# 업데이트 명령어
def update(bot):
    @bot.tree.command(name="업데이트", description="봇의 최신 업데이트 내용을 알려줍니다.")
    @app_commands.guild_only()
    async def update_command(interaction: discord.Interaction):
        try:
            if not os.path.exists('updates.json'):
                await interaction.response.send_message("업데이트 내용 파일을 찾을 수 없습니다.", ephemeral=True)
                return

            with open('updates.json', 'r', encoding='utf-8') as file:
                updates = json.load(file)

            total_updates = len(updates)
            if total_updates == 0:
                await interaction.response.send_message("등록된 업데이트 내용이 없습니다.", ephemeral=True)
                return

        # 첫 번째 페이지 보여주기
            await interaction.response.defer(ephemeral=True)
            await show_update_page(interaction, updates, 1)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

async def show_update_page(interaction, updates, page):
    updates_per_page = 3
    total_updates = len(updates)
    total_pages = (total_updates + updates_per_page - 1) // updates_per_page

    start = (page - 1) * updates_per_page
    end = start + updates_per_page
    page_updates = updates[start:end]

    embed = discord.Embed(title="📢 봇 업데이트 내용", color=discord.Color.blue())
    for update in page_updates:
        details = "\n".join(update['details'])
        embed.add_field(
            name=f"{update['version']} - {update['date']}",
            value=f"{details}\n{'-'*30}",
            inline=False
        )

    view = UpdateView(page, total_pages, updates)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class UpdateView(discord.ui.View):
    def __init__(self, current_page, total_pages, updates):
        super().__init__()
        self.current_page = current_page
        self.total_pages = total_pages
        self.updates = updates

        if current_page > 1:
            self.add_item(UpdateButton("이전", "prev"))
        if current_page < total_pages:
            self.add_item(UpdateButton("다음", "next"))

class UpdateButton(discord.ui.Button):
    def __init__(self, label, direction):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.direction = direction

    async def callback(self, interaction: discord.Interaction):
        view: UpdateView = self.view
        if self.direction == "prev":
            view.current_page -= 1
        else:
            view.current_page += 1
        await show_update_page(interaction, view.updates, view.current_page)
        
def validate_updates_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            updates = json.load(file)
        
        for update in updates:
            if not all(key in update for key in ("version", "date", "details")):
                return False
            if not isinstance(update['version'], str):
                return False
            if not isinstance(update['date'], str):
                return False
            if not isinstance(update['details'], list) or not all(isinstance(detail, str) for detail in update['details']):
                return False
        
        return True
    except (json.JSONDecodeError, FileNotFoundError):
        return False