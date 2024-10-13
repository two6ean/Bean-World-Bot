import random
import asyncio
import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands
from discord import app_commands
from src.database.coin_management import update_user_coins, get_user_coins
from src.config.coin_setup import format_coins
from src.database.game_stats import update_blackjack_stats
import os
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

class BlackjackGame:
    def __init__(self, bet, user):
        self.deck = BlackjackGame.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.bet = bet
        self.user = user
        self.game_over = False
        self.timeout_task = None
        self.deal_initial_cards()

    @staticmethod
    def create_deck():
        suits = ['♥️', '♦️', '♣️', '♠️']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(value, suit) for suit in suits for value in values]
        random.shuffle(deck)
        return deck

    def deal_card(self, hand):
        hand.append(self.deck.pop())

    def deal_initial_cards(self):
        for _ in range(2):
            self.deal_card(self.player_hand)
            self.deal_card(self.dealer_hand)

    def calculate_hand_value(self, hand):
        value_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}
        value = sum(value_map[card[0]] for card in hand)
        num_aces = sum(1 for card in hand if card[0] == 'A')

        while value > 21 and num_aces:
            value -= 10
            num_aces -= 1

        return value

    def player_can_hit(self):
        return self.calculate_hand_value(self.player_hand) < 21

    def dealer_can_hit(self):
        return self.calculate_hand_value(self.dealer_hand) < 18

    def check_winner(self):
        player_value = self.calculate_hand_value(self.player_hand)
        dealer_value = self.calculate_hand_value(self.dealer_hand)

        if dealer_value > 21:
            return '플레이어 승리! 🎉'
        elif player_value > 21:
            return '딜러 승리! 😢'
        elif player_value > dealer_value:
            return '플레이어 승리! 🎉'
        elif player_value < dealer_value:
            return '딜러 승리! 😢'
        else:
            return '무승부! 😐'

    async def handle_timeout(self, interaction: discord.Interaction):
        await asyncio.sleep(60)
        if not self.game_over:
            self.game_over = True
            await interaction.followup.send(
                embed=Embed(title="🃏 블랙잭 게임 결과", description="타임아웃으로 패배! 😢", color=discord.Color.red())
            )

def blackjack(bot: commands.Bot):
    if not hasattr(bot, 'blackjack_games'):
        bot.blackjack_games = {}

    @bot.tree.command(name="블랙잭", description="블랙잭 게임을 시작합니다.")
    @app_commands.describe(bet="베팅할 코인 수")
    @app_commands.guild_only()
    async def blackjack_command(interaction: discord.Interaction, bet: int):
        user_id = interaction.user.id

        if bet > get_user_coins(user_id):
            await interaction.response.send_message("베팅할 코인이 부족합니다.", ephemeral=True)
            return

        update_user_coins(user_id, -bet)
        game = BlackjackGame(bet, interaction.user)
        bot.blackjack_games[user_id] = game

        await show_hands(interaction, game, initial=True)
        game.timeout_task = asyncio.create_task(game.handle_timeout(interaction))

class BlackjackView(ui.View):
    def __init__(self, game: BlackjackGame, interaction: discord.Interaction):
        super().__init__()
        self.game = game
        self.interaction = interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.interaction.user:
            await interaction.response.send_message("당신이 시작한 게임이 아닙니다.", ephemeral=True)
            return False
        if self.game.game_over:
            await interaction.response.send_message("이미 종료된 게임입니다.", ephemeral=True)
            return False
        return True

    @ui.button(label="카드 추가", style=ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

        game = self.game
        if game is None:
            await interaction.followup.send("먼저 블랙잭 게임을 시작하세요.", ephemeral=True)
            return

        game.deal_card(game.player_hand)

        if not game.player_can_hit():
            await self.finish_game(interaction)
        else:
            await show_hands(interaction, game)

    @ui.button(label="카드 유지", style=ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

        game = self.game
        if game is None:
            await interaction.followup.send("먼저 블랙잭 게임을 시작하세요.", ephemeral=True)
            return

        while game.dealer_can_hit():
            game.deal_card(game.dealer_hand)

        await self.finish_game(interaction)

    async def finish_game(self, interaction: discord.Interaction):
        game = self.game
        if game is None:
            await interaction.followup.send("게임 정보가 없습니다.", ephemeral=True)
            return

        game.game_over = True
        result = game.check_winner()

        if result == '플레이어 승리! 🎉':
            update_user_coins(interaction.user.id, game.bet * 2)
        elif result == '무승부! 😐':
            update_user_coins(interaction.user.id, game.bet)

        await show_hands(interaction, game)

        # 버튼 제거
        self.clear_items()

        await interaction.edit_original_response(embed=Embed(
            title="🃏 블랙잭 게임 결과",
            description=f"게임 종료! 결과: {result}\n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
            color=discord.Color.green()
        ), view=self)

        # 게임 로그 기록
        await log_game(interaction.user, game.player_hand, game.dealer_hand, result)

        if game.timeout_task:
            game.timeout_task.cancel()

async def log_game(user, player_hand, dealer_hand, result):
    log_dir = "blackjack_logs"
    os.makedirs(log_dir, exist_ok=True)
    log_filename = os.path.join(log_dir, f"blackjack_log_{datetime.now().strftime('%Y-%m-%d')}.txt")

    # UTF-8 인코딩으로 파일을 엽니다
    with open(log_filename, 'a', encoding='utf-8') as log_file:
        log_file.write(f"플레이어: {user.display_name} ({user.id})\n")  # 닉네임 옆에 유저 ID 추가
        log_file.write(f"플레이어 손패: {' | '.join([f'{value}{suit}' for value, suit in player_hand])}\n")
        log_file.write(f"딜러 손패: {' | '.join([f'{value}{suit}' for value, suit in dealer_hand])}\n")
        log_file.write(f"결과: {result}\n")
        log_file.write(f"--- 게임 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n")

# 손패를 보여주는 함수
async def show_hands(interaction: discord.Interaction, game: BlackjackGame, initial=False):
    player_hand = ' | '.join([f'{value}{suit}' for value, suit in game.player_hand])
    dealer_hand = ' | '.join([f'{value}{suit}' for value, suit in game.dealer_hand[:1]]) + " | ???" if initial else ' | '.join([f'{value}{suit}' for value, suit in game.dealer_hand])

    embed = Embed(title="🃏 블랙잭 게임", color=discord.Color.green())
    embed.add_field(name=f"{game.user.display_name}의 손패", value=player_hand, inline=False)
    embed.add_field(name="🤖 딜러 손패", value=dealer_hand, inline=False)

    view = BlackjackView(game, interaction)

    if not interaction.response.is_done():
        await interaction.response.defer()

    try:
        await interaction.edit_original_response(embed=embed, view=view)
    except discord.errors.NotFound:
        await interaction.response.send_message(embed=embed, view=view)