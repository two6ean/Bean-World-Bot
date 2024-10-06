import random
import asyncio
import discord
from discord import ui, Embed, ButtonStyle
from discord.ext import commands, tasks
from discord import app_commands
from src.database.coin_management import update_user_coins, get_user_coins
from src.config.coin_setup import format_coins
from src.database.game_stats import update_blackjack_stats

intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # 멤버 관련 이벤트를 처리하기 위해 활성화
bot = commands.Bot(command_prefix="!", intents=intents)

class BlackjackGame:
    def __init__(self, bet, user, user_name):
        self.deck = self.create_deck()
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.bet = bet
        self.user = user
        self.user_name = user_name
        self.timeout_task = None

    def create_deck(self):
        suits = ['♥️', '♦️', '♣️', '♠️']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [(value, suit) for suit in suits for value in values]
        random.shuffle(deck)
        return deck

    def deal_card(self, hand):
        hand.append(self.deck.pop())

    def calculate_hand(self, hand):
        value_dict = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10, 'A': 11}
        value = sum(value_dict[card[0]] for card in hand)
        num_aces = sum(1 for card in hand if card[0] == 'A')
        while value > 21 and num_aces:
            value -= 10
            num_aces -= 1
        return value

    def player_turn(self):
        return self.calculate_hand(self.player_hand) < 21

    def dealer_turn(self):
        return self.calculate_hand(self.dealer_hand) < 17

    def check_winner(self):
        player_value = self.calculate_hand(self.player_hand)
        dealer_value = self.calculate_hand(self.dealer_hand)
        if dealer_value > 21 or (player_value <= 21 and player_value > dealer_value):
            return '플레이어 승리! 🎉'
        elif player_value > 21 or dealer_value > player_value:
            return '딜러 승리! 😢'
        else:
            return '무승부! 😐'
    
async def handle_timeout(interaction: discord.Interaction, game: BlackjackGame):
    await asyncio.sleep(60)  # 60초 대기
    if not game.game_over:
        game.game_over = True
        result = "타임아웃으로 패배! 😢"
        await show_hands(interaction, game)
        await interaction.followup.send(embed=discord.Embed(
            title="🃏 블랙잭 게임 결과",
            description=f"게임 종료! 타임아웃으로 자동 종료되었습니다. 결과: {result} \n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
            color=discord.Color.red()
        ))

# bot 객체에 blackjack_games 속성을 추가합니다.
bot.blackjack_games = {}

# 블랙잭 명령어
def blackjack(bot):
    @bot.tree.command(name="블랙잭", description="블랙잭 게임을 시작합니다.")
    @app_commands.describe(bet="베팅할 코인 수")
    @app_commands.guild_only()
    async def blackjack_command(interaction: discord.Interaction, bet: int):
        try:
            user_id = interaction.user.id
            user = interaction.user
            user_name = interaction.user.display_name

            if bet > get_user_coins(user_id):
                await interaction.response.send_message("베팅할 코인이 부족합니다.", ephemeral=True)
                return
            update_user_coins(user_id, -bet)
            game = BlackjackGame(bet, user, user_name)
            game.deal_card(game.player_hand)
            game.deal_card(game.dealer_hand)
            game.deal_card(game.player_hand)
            game.deal_card(game.dealer_hand)
            bot.blackjack_games[user_id] = game
            await show_hands(interaction, game, initial=True)

        # 타임아웃 설정
            game.timeout_task = asyncio.create_task(handle_timeout(interaction, game))
        except Exception as e:
            try:
                await interaction.followup.send(f"오류 발생: {str(e)}", ephemeral=True)
            except discord.errors.NotFound:
                await interaction.response.send_message(f"오류 발생: {str(e)}", ephemeral=True)

class BlackjackView(discord.ui.View):
    def __init__(self, game, interaction: discord.Interaction):
        super().__init__()
        self.game = game
        self.interaction = interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("이 게임은 당신이 시작한 게임이 아닙니다.", ephemeral=True)
            return False
        if self.game.game_over:
            await interaction.response.send_message("이미 종료된 게임입니다.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="카드 추가", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_hit(interaction)

    @discord.ui.button(label="카드 유지", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_stand(interaction)

    async def handle_hit(self, interaction: discord.Interaction):
        game = bot.blackjack_games.get(interaction.user.id)
        if game is None:
            await interaction.response.send_message("블랙잭 게임을 먼저 시작하세요. /블랙잭 명령어를 사용하세요.", ephemeral=True)
            return
        game.deal_card(game.player_hand)
        if not game.player_turn():
            game.game_over = True
            while game.dealer_turn():
                game.deal_card(game.dealer_hand)
            result = game.check_winner()
            net_coins = game.bet if result == '플레이어 승리! 🎉' else -game.bet if result == '딜러 승리! 😢' else 0
            update_blackjack_stats(game.user.id, 'win' if result == '플레이어 승리! 🎉' else 'loss' if result == '딜러 승리! 😢' else 'tie', net_coins)
            await show_hands(interaction, game)
            if result == '플레이어 승리! 🎉':
                update_user_coins(interaction.user.id, game.bet * 2)
            elif result == '무승부! 😐':
                update_user_coins(interaction.user.id, game.bet)
            await interaction.followup.send(embed=discord.Embed(
                title="🃏 블랙잭 게임 결과",
                description=f"게임 종료! 결과: {result}\n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
                color=discord.Color.green()
            ))
        else:
            await show_hands(interaction, game)

        # 타임아웃 리셋
        if game.timeout_task:
            game.timeout_task.cancel()
        game.timeout_task = asyncio.create_task(handle_timeout(interaction, game))

    async def handle_stand(self, interaction: discord.Interaction):
        game = bot.blackjack_games.get(interaction.user.id)
        if game is None:
            await interaction.response.send_message("블랙잭 게임을 먼저 시작하세요. /블랙잭 명령어를 사용하세요.", ephemeral=True)
            return
        while game.dealer_turn():
            game.deal_card(game.dealer_hand)
        game.game_over = True
        result = game.check_winner()
        net_coins = game.bet if result == '플레이어 승리! 🎉' else -game.bet if result == '딜러 승리! 😢' else 0
        update_blackjack_stats(game.user.id, 'win' if result == '플레이어 승리! 🎉' else 'loss' if result == '딜러 승리! 😢' else 'tie', net_coins)
        await show_hands(interaction, game)
        if result == '플레이어 승리! 🎉':
            update_user_coins(interaction.user.id, game.bet * 2)
        elif result == '무승부! 😐':
            update_user_coins(interaction.user.id, game.bet)
        await interaction.followup.send(embed=discord.Embed(
            title="🃏 블랙잭 게임 결과",
            description=f"게임 종료! 결과: {result}\n현재 코인: {format_coins(get_user_coins(interaction.user.id))}개 🪙",
            color=discord.Color.green()
        ))

        # 타임아웃 취소
        if game.timeout_task:
            game.timeout_task.cancel()

async def show_hands(interaction: discord.Interaction, game, initial=False):
    player_hand = ' | '.join([f'{value}{suit}' for value, suit in game.player_hand])
    dealer_hand = ' | '.join([f'{value}{suit}' for value, suit in game.dealer_hand[:1]]) + " | ???" if initial else ' | '.join([f'{value}{suit}' for value, suit in game.dealer_hand])
    embed = discord.Embed(title="🃏 블랙잭 게임", color=discord.Color.green())
    embed.add_field(name=f"{game.user.display_name}의 손패", value=player_hand, inline=False)
    embed.add_field(name="🤖 딜러 손패", value=dealer_hand, inline=False)
    view = BlackjackView(game, interaction)

    if not interaction.response.is_done():
        await interaction.response.defer()

    try:
        await interaction.followup.send(embed=embed, view=view)
    except discord.errors.NotFound:
        await interaction.response.send_message(embed=embed, view=view)