import sqlite3

from src.database.db import get_cursor, get_connection

c = get_cursor()
conn = get_connection()

def ensure_user_stats_exist(user_id):
    c.execute("SELECT 1 FROM game_stats WHERE user_id = ?", (user_id,))
    if c.fetchone() is None:
        c.execute("INSERT INTO game_stats (user_id) VALUES (?)", (user_id,))
        conn.commit()

def update_rps_stats(user_id, result, bet):
    ensure_user_stats_exist(user_id)
    net_coins = 0
    if result == "승리":
        c.execute("UPDATE game_stats SET rps_wins = rps_wins + 1, rps_net_coins = rps_net_coins + ? WHERE user_id = ?", (net_coins, user_id))
    elif result == "패배":
        net_coins = -bet
        c.execute("UPDATE game_stats SET rps_losses = rps_losses + 1, rps_net_coins = rps_net_coins - ? WHERE user_id = ?", (bet, user_id))
    else:
        net_coins = 0
        c.execute("UPDATE game_stats SET rps_ties = rps_ties + 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def update_odd_even_stats(user_id, result, bet):
    ensure_user_stats_exist(user_id)
    if result == "승리":
        net_coins = int(bet * 0.5)  # 승리 시 50% 추가
        c.execute("UPDATE game_stats SET odd_even_wins = odd_even_wins + 1, odd_even_net_coins = odd_even_net_coins + ? WHERE user_id = ?", (net_coins, user_id))
    elif result == "패배":
        c.execute("UPDATE game_stats SET odd_even_losses = odd_even_losses + 1, odd_even_net_coins = odd_even_net_coins - ? WHERE user_id = ?", (bet, user_id))
    conn.commit()

def update_slot_machine_stats(user_id, result, payout, bet):
    ensure_user_stats_exist(user_id)
    if result == "승리":
        net_coins = payout - bet
        c.execute("UPDATE game_stats SET slot_machine_wins = slot_machine_wins + 1, slot_machine_net_coins = slot_machine_net_coins + ? WHERE user_id = ?", (net_coins, user_id))
    else:
        c.execute("UPDATE game_stats SET slot_machine_losses = slot_machine_losses + 1, slot_machine_net_coins = slot_machine_net_coins - ? WHERE user_id = ?", (bet, user_id))
    conn.commit()

def update_blackjack_stats(user_id, result, net_coins):
    c.execute("SELECT blackjack_wins, blackjack_losses, blackjack_ties, blackjack_net_coins FROM game_stats WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    
    if row is None:
        wins, losses, ties = 0, 0, 0
        if result == 'win':
            wins = 1
        elif result == 'loss':
            losses = 1
        else:
            ties = 1
        c.execute("INSERT INTO game_stats (user_id, blackjack_wins, blackjack_losses, blackjack_ties, blackjack_net_coins) VALUES (?, ?, ?, ?, ?)", (user_id, wins, losses, ties, net_coins))
    else:
        wins, losses, ties, current_net_coins = row
        if result == 'win':
            wins += 1
        elif result == 'loss':
            losses += 1
        else:
            ties += 1
        c.execute("UPDATE game_stats SET blackjack_wins = ?, blackjack_losses = ?, blackjack_ties = ?, blackjack_net_coins = ? WHERE user_id = ?", (wins, losses, ties, current_net_coins + net_coins, user_id))
    conn.commit()