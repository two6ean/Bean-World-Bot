import random
import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.coin_management import get_user_coins, update_user_coins
from src.database.game_stats import update_slot_machine_stats
from src.config.coin_setup import format_coins

# 슬롯머신 명령어
def slot(bot):
    @bot.tree.command(name="슬롯머신", description="슬롯머신 게임을 시작합니다.")
    @app_commands.describe(bet="베팅할 코인 수")
    @app_commands.guild_only()
    async def slot_machine_command(interaction: discord.Interaction, bet: int):
        try:
            user_id = interaction.user.id
            if bet > get_user_coins(user_id):
                await interaction.response.send_message("베팅할 코인이 부족합니다.", ephemeral=True)
                return

            update_user_coins(user_id, -bet)
            emojis = ['🍒', '🍋', '🍊', '🍉', '7️⃣', '💰', '🎁', '🎈', '🐲', '💣', '⚽', '🏆']
            result = [random.choice(emojis) for _ in range(3)]
            result_str = ' | '.join(result)
            payout = 0
            net_coins = -bet
            is_jackpot = False
            is_super_jackpot = False

            if result[0] == result[1] == result[2] == '7️⃣':
                payout = bet * 100  # 7️⃣ 3개가 나오면 100배 지급
                is_super_jackpot = True
            elif result[0] == result[1] == result[2]:
                payout = bet * 10  # 잭팟: 같은 기호 3개가 나오면 10배 지급
                is_jackpot = True
            elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                payout = bet * 2

            update_user_coins(user_id, payout)
            net_coins += payout

            if payout > 0:
                update_slot_machine_stats(user_id, "승리", payout, bet)
            else:
                update_slot_machine_stats(user_id, "패배", 0, bet)

            embed = discord.Embed(
                title="슬롯머신 결과",
                description=f"🎰 슬롯머신 결과: {result_str} 🎰\n획득 코인: {format_coins(payout)}개 🪙\n현재 코인: {format_coins(get_user_coins(user_id))}개 🪙",
                color=discord.Color.green() if payout > 0 else discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)

            if is_super_jackpot:
                super_jackpot_embed = discord.Embed(
                    title="🎉 슈퍼 잭팟! 🎉",
                    description=f"축하합니다! {interaction.user.mention}님이 슬롯머신에서 슈퍼 잭팟을 터뜨렸습니다! 💰\n획득 코인: {format_coins(payout)}개 🪙",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=super_jackpot_embed)
            elif is_jackpot:
                jackpot_embed = discord.Embed(
                    title="🎉 잭팟! 🎉",
                    description=f"축하합니다! {interaction.user.mention}님이 슬롯머신에서 잭팟을 터뜨렸습니다! 💰\n획득 코인: {format_coins(payout)}개 🪙",
                    color=discord.Color.gold()
                )
                await interaction.followup.send(embed=jackpot_embed)

        except Exception as e:
            await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)