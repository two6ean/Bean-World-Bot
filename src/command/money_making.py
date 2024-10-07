import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

class MoneyMakingView(discord.ui.View):
    def __init__(self, user_id, button_states=None, page=0, buttons_clicked=0):
        super().__init__(timeout=300)  # 5분 타임아웃 설정
        self.user_id = user_id
        self.page = page
        self.buttons_clicked = buttons_clicked
        self.button_states = button_states if button_states else [False] * 20
        self.buttons = []

        start = page * 10
        end = start + 10
        for i in range(start, end):
            button = discord.ui.Button(label="⬜", custom_id=f"work_{i+1}", style=discord.ButtonStyle.success if self.button_states[i] else discord.ButtonStyle.primary)
            button.callback = self.on_button_click
            button.disabled = self.button_states[i]
            self.add_item(button)
            self.buttons.append(button)

        if page > 0:
            prev_button = discord.ui.Button(label="이전", style=discord.ButtonStyle.secondary)
            prev_button.callback = self.prev_page
            self.add_item(prev_button)

        if end < 20:
            next_button = discord.ui.Button(label="다음", style=discord.ButtonStyle.secondary)
            next_button.callback = self.next_page
            self.add_item(next_button)

    async def on_button_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 작업은 당신이 시작한 작업이 아닙니다.", ephemeral=True)
            return

        self.buttons_clicked += 1
        button_index = int(interaction.data['custom_id'].split('_')[1]) - 1
        self.button_states[button_index] = True
        button = discord.utils.get(self.buttons, custom_id=interaction.data['custom_id'])
        button.style = discord.ButtonStyle.success
        button.disabled = True
        await interaction.response.edit_message(view=self)

        if self.buttons_clicked == 20:
            update_user_coins(self.user_id, 20)
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="노가다 완료!",
                    description=f"20개의 버튼을 모두 클릭하여 20개의 코인을 획득했습니다! 현재 코인: {format_coins(get_user_coins(self.user_id))}개 🪙",
                    color=discord.Color.green()
                )
            )
            update_daily_tasks(self.user_id, "노가다")
            bot.ongoing_tasks.remove(self.user_id)
            self.stop()
        else:
            embed = discord.Embed(
                title="노가다 작업",
                description=f"{self.buttons_clicked}/20 버튼을 클릭했습니다.",
                color=discord.Color.blue()
            )
            await interaction.edit_original_response(embed=embed, view=self)

    async def prev_page(self, interaction: discord.Interaction):
        self.page -= 1
        await interaction.response.edit_message(view=MoneyMakingView(self.user_id, self.button_states, self.page, self.buttons_clicked))

    async def next_page(self, interaction: discord.Interaction):
        self.page += 1
        await interaction.response.edit_message(view=MoneyMakingView(self.user_id, self.button_states, self.page, self.buttons_clicked))


class ArithmeticProblemView(discord.ui.View):
    def __init__(self, user_id, correct_answer):
        super().__init__(timeout=300)  # 5분 타임아웃 설정
        self.user_id = user_id
        self.correct_answer = correct_answer

        choices = [correct_answer, correct_answer + random.randint(1, 10), correct_answer - random.randint(1, 10), correct_answer + random.randint(11, 20)]
        random.shuffle(choices)

        for choice in choices:
            button = discord.ui.Button(label=str(choice), custom_id=str(choice))
            button.callback = self.on_button_click
            self.add_item(button)

    async def on_button_click(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("이 작업은 당신이 시작한 작업이 아닙니다.", ephemeral=True)
            return

        selected_answer = int(interaction.data['custom_id'])
        if selected_answer == self.correct_answer:
            update_user_coins(self.user_id, 10)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="정답입니다!",
                    description=f"10개의 코인을 획득했습니다! 현재 코인: {format_coins(get_user_coins(self.user_id))}개 🪙",
                    color=discord.Color.green()
                )
            )
            update_daily_tasks(self.user_id, "문제풀기")
            bot.ongoing_tasks.remove(self.user_id)
            self.stop()
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="오답입니다!",
                    description="다시 시도하세요!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

    async def on_timeout(self):
        await self.message.edit(
            embed=discord.Embed(
                title="시간 초과",
                description="시간이 초과되었습니다. 다시 시도해주세요.",
                color=discord.Color.red()
            ),
            view=None
        )
        bot.ongoing_tasks.remove(self.user_id)

bot.ongoing_tasks = set()

def check_and_reset_daily_tasks(user_id):
    current_time = get_korean_time()
    reset = False

    c.execute("SELECT last_reset, work_count, problem_count FROM daily_tasks WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if row:
        last_reset, work_count, problem_count = row
        last_reset_time = datetime.fromisoformat(last_reset).astimezone(KST)
        if (current_time - last_reset_time).total_seconds() >= 86400: 
            reset = True
            work_count = 0
            problem_count = 0
            c.execute("UPDATE daily_tasks SET last_reset = ?, work_count = ?, problem_count = ? WHERE user_id = ?", (current_time.isoformat(), work_count, problem_count, user_id))
            conn.commit()
    else:
        reset = True
        work_count = 0
        problem_count = 0
        c.execute("INSERT INTO daily_tasks (user_id, last_reset, work_count, problem_count) VALUES (?, ?, ?, ?)", (user_id, current_time.isoformat(), work_count, problem_count))
        conn.commit()

    return reset, work_count, problem_count, current_time

def money_making(bot):
    @bot.tree.command(name="돈벌기", description="노가다 또는 문제풀기를 선택하여 돈을 법니다.")
    @app_commands.choices(option=[
        app_commands.Choice(name="노가다", value="노가다"),
        app_commands.Choice(name="문제풀기", value="문제풀기")
    ])
    @app_commands.guild_only()
    async def money_making_command(interaction: discord.Interaction, option: app_commands.Choice[str]):
        try:
            user_id = interaction.user.id
            reset, work_count, problem_count, last_reset_time = check_and_reset_daily_tasks(user_id)
            current_time = get_korean_time()

            if option.value == "노가다":
                if work_count >= 5:
                    time_diff = (current_time - last_reset_time).total_seconds()
                    time_remaining = 86400 - time_diff
                    hours, remainder = divmod(time_remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="노가다 제한",
                            description=f"오늘은 더 이상 노가다 작업을 할 수 없습니다. 내일 다시 시도하세요. 남은 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                if user_id in bot.ongoing_tasks:
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="진행 중인 작업",
                            description="이미 진행 중인 노가다 작업이 있습니다.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                embed = discord.Embed(
                    title="노가다 작업",
                    description="20개의 버튼을 클릭하여 20개의 코인을 획득하세요!",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed)
                message = await interaction.original_response()
                view = MoneyMakingView(user_id)
                await message.edit(view=view)
                bot.ongoing_tasks.add(user_id)
            elif option.value == "문제풀기":
                if problem_count >= 5:
                    time_diff = (current_time - last_reset_time).total_seconds()
                    time_remaining = 86400 - time_diff
                    hours, remainder = divmod(time_remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="문제풀기 제한",
                            description=f"오늘은 더 이상 문제풀기를 할 수 없습니다. 내일 다시 시도하세요. 남은 시간: {int(hours)}시간 {int(minutes)}분 {int(seconds)}초",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                if user_id in bot.ongoing_tasks:
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title="진행 중인 작업",
                            description="이미 진행 중인 문제풀기 작업이 있습니다.",
                            color=discord.Color.red()
                        ),
                        ephemeral=True
                    )
                    return
                num1 = random.randint(1, 50)
                num2 = random.randint(1, 50)
                operator = random.choice(['+', '-', '*', '/'])
                if operator == '+':
                    correct_answer = num1 + num2
                elif operator == '-':
                    correct_answer = num1 - num2
                elif operator == '*':
                    correct_answer = num1 * num2
                else:
                    num1 = num1 * num2
                    correct_answer = num1 // num2

                problem_text = f"{num1} {operator} {num2} = ?"
                view = ArithmeticProblemView(user_id, correct_answer)
                embed = discord.Embed(
                    title="문제풀기",
                    description=f"다음 문제를 풀어주세요: `{problem_text}`",
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, view=view)
                bot.ongoing_tasks.add(user_id)
            else:
                await interaction.response.send_message("올바르지 않은 옵션입니다.", ephemeral=True)
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)
            else:
                await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)