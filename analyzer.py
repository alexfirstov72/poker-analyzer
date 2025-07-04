import re
import os
import csv
import matplotlib.pyplot as plt

# Список позиций
POSITIONS = ["UTG", "UTG+1", "MP", "HJ", "CO", "BTN", "SB", "BB"]

# Статистика
stats = {pos: {"hands": 0, "profit_bb": 0} for pos in POSITIONS}
total_stats = {"hands": 0, "profit_bb": 0}

# VPIP / PFR
vpip_data = {pos: {"vpip_hands": 0, "total_hands": 0} for pos in POSITIONS}
pfr_data = {pos: {"pfr_hands": 0, "total_hands": 0} for pos in POSITIONS}

# Winrate
winrate_data = {"hands_played": 0, "hands_won": 0}

# ROI
roi_data = {"buy_ins": 0, "total_profit": 0}

# Showdown / Non-showdown
showdown_wins = 0
non_showdown_wins = 0
ev_by_hand_type = {
    "showdown": {"bb": 0, "hands": 0},
    "non_showdown": {"bb": 0, "hands": 0},
    "gto_like": {"bb": 0, "hands": 0}
}


def get_hero_position(button_seat, hero_seat):
    """Возвращает позицию героя относительно кнопки"""
    offset = (hero_seat - button_seat) % 8
    mapping = {
        0: "BTN",
        1: "SB",
        2: "BB",
        3: "UTG",
        4: "UTG+1",
        5: "MP",
        6: "HJ",
        7: "CO"
    }
    return mapping.get(offset, "Unknown")


def parse_hand(hand_text):
    data = {
        "hand_complete": False,
        "hero_in_game": False,
        "hero_position": "Unknown",
        "bb_size": 0,
        "ante": 0,
        "start_stack": 0,
        "end_stack": 0,
        "profit": 0,
        "actions": [],
        "showdown_win": False,
        "non_showdown_win": False,
        "is_gto_like": False
    }

    lines = hand_text.strip().split('\n')

    seat_map = {}
    button_seat = None
    hero_seat = None
    ante_total = 0
    sb_size = 0
    bb_size = 0

    for line in lines:
        if "Table" in line and "button" in line:
            match = re.search(r"Seat #(\d+) is the button", line)
            if match:
                button_seat = int(match.group(1))

        if "Hero:" in line and "folds" in line:
            data["actions"].append("fold")
        elif "Hero:" in line and "raises" in line:
            data["actions"].append("raise")
        elif "Hero:" in line and ("calls" in line or "bets" in line):
            data["actions"].append("call")
        elif "Hero:" in line and "checks" in line:
            data["actions"].append("check")

        if "posts small blind" in line:
            match = re.search(r"posts small blind ([\d,]+)", line)
            if match:
                sb_size = int(match.group(1).replace(',', ''))

        if "posts big blind" in line:
            match = re.search(r"posts big blind ([\d,]+)", line)
            if match:
                bb_size = int(match.group(1).replace(',', ''))

        if "Hero" in line and "Dealt to Hero" in line:
            data["hand_complete"] = True

        seat_match = re.search(r"Seat (\d+): Hero \$$(.+?) in chips\$$", line)
        if seat_match:
            hero_seat = int(seat_match.group(1))
            stack = int(seat_match.group(2).replace(',', ''))
            data["start_stack"] = stack
            data["hero_in_game"] = True

    if not data["hero_in_game"]:
        return data

    data["bb_size"] = bb_size
    data["ante"] = ante_total

    final_stack_match = re.search(r"Hero: shows.*?\$$(\d+,?\d*) in chips\$$", hand_text)
    if final_stack_match:
        data["end_stack"] = int(final_stack_match.group(1).replace(',', ''))
    else:
        data["end_stack"] = data["start_stack"]

    data["profit"] = data["end_stack"] - data["start_stack"]

    if button_seat and hero_seat:
        data["hero_position"] = get_hero_position(button_seat, hero_seat)

    if "Hero: shows" in hand_text and "collected" in hand_text and data["profit"] > 0:
        data["showdown_win"] = True
        global showdown_wins
        showdown_wins += 1
    elif "collected" in hand_text and not "Hero: shows" in hand_text and data["profit"] > 0:
        data["non_showdown_win"] = True
        global non_showdown_wins
        non_showdown_wins += 1

    return data


def update_stats(data):
    pos = data["hero_position"]
    if data["bb_size"] == 0:
        return

    profit_bb = data["profit"] / data["bb_size"]
    stats[pos]["hands"] += 1
    stats[pos]["profit_bb"] += profit_bb
    total_stats["hands"] += 1
    total_stats["profit_bb"] += profit_bb

    vpip_data[pos]["total_hands"] += 1
    pfr_data[pos]["total_hands"] += 1
    if any(act in data["actions"] for act in ["call", "raise"]):
        vpip_data[pos]["vpip_hands"] += 1
    if "raise" in data["actions"]:
        pfr_data[pos]["pfr_hands"] += 1

    winrate_data["hands_played"] += 1
    if data["profit"] > 0:
        winrate_data["hands_won"] += 1

    roi_data["buy_ins"] += 100
    roi_data["total_profit"] += data["profit"]

    if data["showdown_win"]:
        ev_by_hand_type["showdown"]["bb"] += profit_bb
        ev_by_hand_type["showdown"]["hands"] += 1
    elif data["non_showdown_win"]:
        ev_by_hand_type["non_showdown"]["bb"] += profit_bb
        ev_by_hand_type["non_showdown"]["hands"] += 1

    if "raise" in data["actions"] and "check" in data["actions"]:
        ev_by_hand_type["gto_like"]["bb"] += profit_bb
        ev_by_hand_type["gto_like"]["hands"] += 1


def calculate_and_print_stats():
    print("\n--- EV bb/100 by Position ---")
    for pos in POSITIONS:
        if stats[pos]["hands"] > 0:
            ev = (stats[pos]["profit_bb"] / stats[pos]["hands"]) * 100
            print(f"{pos}: {ev:.2f} bb/100 ({stats[pos]['hands']} рук)")
        else:
            print(f"{pos}: N/A")

    if total_stats["hands"] > 0:
        overall_ev = (total_stats["profit_bb"] / total_stats["hands"]) * 100
        print(f"\n📊 Общий EV: {overall_ev:.2f} bb/100 ({total_stats['hands']} рук)")

    print("\n--- VPIP by Position ---")
    for pos in POSITIONS:
        total = vpip_data[pos]["total_hands"]
        vpip = vpip_data[pos]["vpip_hands"] / total * 100 if total else 0
        print(f"{pos}: {vpip:.1f}% ({vpip_data[pos]['vpip_hands']}/{total})")

    print("\n--- PFR by Position ---")
    for pos in POSITIONS:
        total = pfr_data[pos]["total_hands"]
        pfr = pfr_data[pos]["pfr_hands"] / total * 100 if total else 0
        print(f"{pos}: {pfr:.1f}% ({pfr_data[pos]['pfr_hands']}/{total})")

    print_winrate()
    print_roi()


def print_winrate():
    wr = (winrate_data["hands_won"] / winrate_data["hands_played"]) * 100 if winrate_data["hands_played"] else 0
    print(f"\n🎯 Winrate: {wr:.2f}% ({winrate_data['hands_won']}/{winrate_data['hands_played']})")


def print_roi():
    roi = (roi_data["total_profit"] / roi_data["buy_ins"]) * 100 if roi_data["buy_ins"] else 0
    print(f"\n📈 ROI: {roi:.2f}% (Buy-ins: {roi_data['buy_ins']}, Profit: {roi_data['total_profit']})")


def export_to_csv(filename="poker_stats.csv"):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Position", "EV bb/100", "VPIP", "PFR", "Hands"])

        for pos in POSITIONS:
            ev = (stats[pos]["profit_bb"] / stats[pos]["hands"]) * 100 if stats[pos]["hands"] else 0
            vpip = (vpip_data[pos]["vpip_hands"] / vpip_data[pos]["total_hands"]) * 100 if vpip_data[pos]["total_hands"] else 0
            pfr = (pfr_data[pos]["pfr_hands"] / pfr_data[pos]["total_hands"]) * 100 if pfr_data[pos]["total_hands"] else 0
            writer.writerow([pos, f"{ev:.2f}", f"{vpip:.2f}%", f"{pfr:.2f}%", stats[pos]["hands"]])

    print(f"\n✅ Экспортировано в {filename}")


def plot_combined_chart():
    labels = ["Showdown", "Non-showdown", "Total", "GTO-like"]
    values = [
        (ev_by_hand_type["showdown"]["bb"] / max(ev_by_hand_type["showdown"]["hands"], 1)) * 100,
        (ev_by_hand_type["non_showdown"]["bb"] / max(ev_by_hand_type["non_showdown"]["hands"], 1)) * 100,
        ((ev_by_hand_type["showdown"]["bb"] + ev_by_hand_type["non_showdown"]["bb"]) /
         max(ev_by_hand_type["showdown"]["hands"] + ev_by_hand_type["non_showdown"]["hands"], 1)) * 100,
        (ev_by_hand_type["gto_like"]["bb"] / max(ev_by_hand_type["gto_like"]["hands"], 1)) * 100
    ]

    colors = ['red', 'yellow', 'blue', 'green']
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, values, color=colors)
    plt.ylabel('EV (bb/100)')
    plt.title('Эффективность рук по типам')
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 1, f'{yval:.1f}', ha='center', va='bottom')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("combined_ev_chart.png")
    print("✅ График сохранён как combined_ev_chart.png")
    plt.show()


def main(filename="hands/combined.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()

    hands = content.split("*** HOLE CARDS ***")[1:]
    for idx, hand in enumerate(hands):
        full_hand = "*** HOLE CARDS ***" + hand
        parsed = parse_hand(full_hand)
        if parsed["hero_in_game"]:
            update_stats(parsed)

    calculate_and_print_stats()
    export_to_csv()
    plot_combined_chart()


if __name__ == "__main__":
    main()
