import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.config.coin_setup import format_coins
from src.database.coin_management import get_user_coins, update_user_coins
from src.database.game_stats import update_rps_stats

def rps(bot):
    @bot.tree.command(name="가위바위보", description="가위바위보 게임을 합니다.")
    @app_commands.describe(배팅="배팅할 코인 수", 선택="가위, 바위, 보 중 하나를 선택하세요")
    @app_commands.choices(선택=[
        app_commands.Choice(name="가위", value="가위"),
        app_commands.Choice(name="바위", value="바위"),
        app_commands.Choice(name="보", value="보")
    ])
    @app_commands.guild_only()
    async def rps_command(interaction: discord.Interaction, 배팅: int, 선택: app_commands.Choice[str]):
        try:
            user_id = interaction.user.id
            current_coins = get_user_coins(user_id)
            if 배팅 > current_coins:
                await interaction.response.send_message("배팅할 코인이 부족합니다.", ephemeral=True)
                return

            user_choice = 선택.value
            bot_choice = random.choice(["가위", "바위", "보"])
            result = ""
            net_coins = 0  # net_coins 변수를 초기화합니다.

        # 배팅 금액을 먼저 차감합니다.
            update_user_coins(user_id, -배팅)

            if user_choice == bot_choice:
                result = "무승부"
                net_coins = 배팅  # 무승부 시 배팅 금액 반환
                update_user_coins(user_id, 배팅)  # 반환 처리
            elif (user_choice == "가위" and bot_choice == "보") or \
                (user_choice == "바위" and bot_choice == "가위") or \
                (user_choice == "보" and bot_choice == "바위"):
                result = "승리"
                net_coins = int(배팅 * 1.5)  # 승리 시 배팅 금액의 50% 추가
                update_user_coins(user_id, net_coins)
            else:
                result = "패배"
                net_coins = 0  # 패배 시 net_coins는 이미 차감되었으므로 0

            update_rps_stats(user_id, result, 배팅)

            color = discord.Color.green() if result == "승리" else discord.Color.red() if result == "패배" else discord.Color.orange()
            embed = discord.Embed(
                title="가위바위보 결과",
                description=(
                    f"**{interaction.user.mention}님의 선택:** {user_choice}\n"
                    f"**봇의 선택:** {bot_choice}\n"
                    f"**결과:** {result}\n"
                    f"**변동 코인:** {net_coins - 배팅 if result == '승리' else net_coins} 🪙\n"
                    f"**현재 코인:** {get_user_coins(user_id)} 🪙"
                ),
                color=color
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)