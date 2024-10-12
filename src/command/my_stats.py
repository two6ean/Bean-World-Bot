import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.coin_management import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

def my_stats(bot):
    @bot.tree.command(name="내통계", description="내 게임 통계를 표시합니다.")
    @app_commands.guild_only()
    async def my_stats_command(interaction: discord.Interaction):
        try:
            user_id = interaction.user.id
            c.execute("SELECT * FROM game_stats WHERE user_id = ?", (user_id,))
            row = c.fetchone()

        # 기본값으로 초기화된 통계
            stats = {
                'user_id': user_id,
                'rps_wins': 0, 'rps_losses': 0, 'rps_ties': 0, 'rps_net_coins': 0,
                'odd_even_wins': 0, 'odd_even_losses': 0, 'odd_even_net_coins': 0,
                'slot_machine_wins': 0, 'slot_machine_losses': 0, 'slot_machine_net_coins': 0,
                'blackjack_wins': 0, 'blackjack_losses': 0, 'blackjack_ties': 0, 'blackjack_net_coins': 0,
                'check_in_count': 0, 'work_count': 0, 'problem_count': 0,
                'check_in_net_coins': 0  
            }

            if row:
                keys = list(stats.keys())
                if len(row) != len(keys):
                    return
                for i in range(1, len(row)):  # 첫 번째 값인 user_id는 건너뜁니다.
                    stats[keys[i]] = row[i]

            c.execute("SELECT check_in_count FROM attendance WHERE user_id = ?", (user_id,))
            attendance_row = c.fetchone()
            check_in_count = attendance_row[0] if attendance_row else 0

            embed = discord.Embed(title="📊 내 통계", color=discord.Color.blue())
            embed.add_field(name="✂️ 가위바위보", value=f"승리: {stats['rps_wins']} 패배: {stats['rps_losses']} 무승부: {stats['rps_ties']}\n순 코인: {stats['rps_net_coins']} 🪙", inline=True)
            embed.add_field(name="⚖️ 홀짝", value=f"승리: {stats['odd_even_wins']} 패배: {stats['odd_even_losses']}\n순 코인: {stats['odd_even_net_coins']} 🪙", inline=True)
            embed.add_field(name="🎰 슬롯 머신", value=f"승리: {stats['slot_machine_wins']} 패배: {stats['slot_machine_losses']}\n순 코인: {stats['slot_machine_net_coins']} 🪙", inline=True)
            embed.add_field(name="🃏 블랙잭", value=f"승리: {stats['blackjack_wins']} 패배: {stats['blackjack_losses']} 무승부: {stats['blackjack_ties']}\n순 코인: {stats['blackjack_net_coins']} 🪙", inline=True)
            embed.add_field(name="📅 출석 체크", value=f"출석 횟수: {check_in_count}", inline=True)
            embed.add_field(name="💼 돈 벌기", value=f"노가다: {stats['work_count']} 문제풀기: {stats['problem_count']}", inline=True)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)