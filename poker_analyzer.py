import re
import csv
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st  # УДАЛИТЬ ЭТУ СТРОКУ
from collections import defaultdict
from io import StringIO
import os

class PokerHandParser:
    def __init__(self):
        self.hands = []
        self.current_hand = None
        self.positions = ['UTG', 'UTG1', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB']
        
    def parse_file(self, content):
        lines = content.split('\n')
        for line in lines:
            self.process_line(line)
        if self.current_hand:
            self.finalize_hand()
    
    def process_line(self, line):
        if 'Poker Hand #' in line:
            if self.current_hand:
                self.finalize_hand()
            self.start_new_hand(line)
        elif self.current_hand:
            self.process_hand_line(line)
    
    def start_new_hand(self, line):
        hand_id_match = re.search(r'#(\w+)', line)
        tournament_match = re.search(r'Tournament #(\d+)', line)
        level_match = re.search(r'Level(\d+)\((\d+)/(\d+)\)', line.replace(' ', ''))
        
        self.current_hand = {
            'hand_id': hand_id_match.group(1) if hand_id_match else 'unknown',
            'tournament_id': tournament_match.group(1) if tournament_match else 'unknown',
            'level': {
                'level': int(level_match.group(1)) if level_match else 0,
                'small_blind': int(level_match.group(2)) if level_match else 0,
                'big_blind': int(level_match.group(3)) if level_match else 0
            } if level_match else None,
            'button_seat': None,
            'hero_seat': None,
            'players': {},
            'hero_cards': None,
            'actions': {'preflop': [], 'flop': [], 'turn': [], 'river': []},
            'results': {},
            'position': None,
            'stack': 0,
            'outcome': 0,
            'current_street': None,
            'bounty': 0,
            'invested': 0
        }
    
    def process_hand_line(self, line):
        try:
            # Button seat detection
            if 'Seat #' in line and 'is the button' in line:
                button_match = re.search(r'Seat #(\d+)', line)
                if button_match:
                    self.current_hand['button_seat'] = int(button_match.group(1))
            
            # Hero stack detection
            if 'Seat' in line and 'Hero' in line and 'chips' in line:
                hero_match = re.search(r'Seat (\d+): Hero \((\d+) in chips\)', line)
                if hero_match:
                    self.current_hand['hero_seat'] = int(hero_match.group(1))
                    self.current_hand['stack'] = int(hero_match.group(2))
            
            # Hole cards detection
            if 'Dealt to Hero' in line:
                cards_match = re.search(r'\[([^\]]+)\]', line)
                if cards_match:
                    self.current_hand['hero_cards'] = cards_match.group(1).split()
            
            # Ante posting
            if 'posts the ante' in line and 'Hero' in line:
                ante_match = re.search(r'ante (\d+)', line)
                if ante_match:
                    self.current_hand['invested'] += int(ante_match.group(1))
            
            # Blinds posting
            if 'posts small blind' in line and 'Hero' in line:
                sb_match = re.search(r'blind (\d+)', line)
                if sb_match:
                    self.current_hand['invested'] += int(sb_match.group(1))
                    self.current_hand['position'] = 'SB'
            
            if 'posts big blind' in line and 'Hero' in line:
                bb_match = re.search(r'blind (\d+)', line)
                if bb_match:
                    self.current_hand['invested'] += int(bb_match.group(1))
                    self.current_hand['position'] = 'BB'
            
            # Street detection
            if '*** HOLE CARDS ***' in line:
                self.current_hand['current_street'] = 'preflop'
            
            for street in ['FLOP', 'TURN', 'RIVER']:
                if f'*** {street} ***' in line:
                    self.current_hand['current_street'] = street.lower()
            
            # Hero actions
            if 'Hero:' in line and self.current_hand['current_street']:
                action = line.split('Hero: ')[1].strip()
                self.current_hand['actions'][self.current_hand['current_street']].append(action)
                
                # Track investments
                if 'calls' in action:
                    call_match = re.search(r'calls (\d+)', action)
                    if call_match:
                        self.current_hand['invested'] += int(call_match.group(1))
                elif 'raises' in action:
                    raise_match = re.search(r'raises \d+ to (\d+)', action)
                    if raise_match:
                        self.current_hand['invested'] += int(raise_match.group(1))
                elif 'bets' in action:
                    bet_match = re.search(r'bets (\d+)', action)
                    if bet_match:
                        self.current_hand['invested'] += int(bet_match.group(1))
            
            # Hand results
            if 'collected' in line and 'Hero' in line:
                collected_match = re.search(r'collected (\d+)', line)
                if collected_match:
                    self.current_hand['outcome'] = int(collected_match.group(1)) - self.current_hand['invested']
            
            if 'bounty' in line and 'Hero' in line:
                bounty_match = re.search(r'bounty (\d+)', line)
                if bounty_match:
                    self.current_hand['bounty'] = int(bounty_match.group(1))
        
        except Exception as e:
            st.warning(f"Error processing line: {line}\nError: {str(e)}")
    
    def finalize_hand(self):
        # Calculate position if not set by blinds
        if not self.current_hand['position'] and self.current_hand['hero_seat'] is not None and self.current_hand['button_seat'] is not None:
            self.calculate_position()
        
        # Add hand to collection
        self.hands.append(self.current_hand)
        self.current_hand = None
    
    def calculate_position(self):
        btn = self.current_hand['button_seat']
        hero = self.current_hand['hero_seat']
        
        # Simplified position calculation for 8-max
        diff = (hero - btn) % 8
        position_map = {
            0: 'BTN',
            1: 'SB',
            2: 'BB',
            3: 'UTG',
            4: 'UTG1',
            5: 'MP',
            6: 'HJ',
            7: 'CO'
        }
        
        if diff in position_map:
            self.current_hand['position'] = position_map[diff]

class PokerStatsCalculator:
    def __init__(self, hands):
        self.hands = hands
        self.positions = ['UTG', 'UTG1', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB', 'overall']
        self.stats = {pos: self.create_empty_stats() for pos in self.positions}
    
    def create_empty_stats(self):
        return {
            'hands': 0, 'vpip': 0, 'pfr': 0, 'aggression_factor': 0,
            'fold_cbet_flop': 0, 'cbet_opportunities': 0, 'win_rate': 0, '3bet': 0,
            'won_showdown': 0, 'won_noshow': 0, 'total_won': 0,
            'ev_bb_100': 0, 'chips_start': 0, 'chips_end': 0,
            'bets': 0, 'raises': 0, 'calls': 0, 'folds': 0,
            'total_profit': 0
        }
    
    def calculate_stats(self):
        for hand in self.hands:
            position = hand.get('position')
            if not position or position not in self.positions:
                continue
                
            pos_stats = self.stats[position]
            overall_stats = self.stats['overall']
            
            # Increment hand counts
            pos_stats['hands'] += 1
            overall_stats['hands'] += 1
            
            # Track starting and ending chips
            pos_stats['chips_start'] += hand['stack']
            profit = hand['outcome'] + hand.get('bounty', 0)
            pos_stats['chips_end'] += hand['stack'] + profit
            pos_stats['total_profit'] += profit
            overall_stats['total_profit'] += profit
            
            # VPIP (Voluntarily Put $ In Pot)
            preflop_actions = hand['actions']['preflop']
            if any(action in ['raises', 'calls', 'bets'] for action in preflop_actions):
                pos_stats['vpip'] += 1
                overall_stats['vpip'] += 1
            
            # PFR (Pre-Flop Raise)
            if any('raises' in action for action in preflop_actions):
                pos_stats['pfr'] += 1
                overall_stats['pfr'] += 1
            
            # Aggression Factor
            actions = [a for street in hand['actions'].values() for a in street]
            bets_raises = sum(1 for a in actions if 'bets' in a or 'raises' in a)
            calls = sum(1 for a in actions if 'calls' in a)
            folds = sum(1 for a in actions if 'folds' in a)
            
            pos_stats['bets'] += bets_raises
            pos_stats['calls'] += calls
            pos_stats['folds'] += folds
            overall_stats['bets'] += bets_raises
            overall_stats['calls'] += calls
            overall_stats['folds'] += folds
            
            # Fold to CBet Flop
            flop_actions = hand['actions']['flop']
            if flop_actions and flop_actions[0] == 'folds':
                pos_stats['fold_cbet_flop'] += 1
                overall_stats['fold_cbet_flop'] += 1
            
            if flop_actions:
                pos_stats['cbet_opportunities'] += 1
                overall_stats['cbet_opportunities'] += 1
            
            # 3-Bet
            if len([a for a in preflop_actions if 'raises' in a]) >= 2:
                pos_stats['3bet'] += 1
                overall_stats['3bet'] += 1
            
            # Win tracking
            if hand['outcome'] > 0 or hand.get('bounty', 0) > 0:
                pos_stats['total_won'] += 1
                overall_stats['total_won'] += 1
                
                if any('shows' in a for a in actions):
                    pos_stats['won_showdown'] += 1
                    overall_stats['won_showdown'] += 1
                else:
                    pos_stats['won_noshow'] += 1
                    overall_stats['won_noshow'] += 1
        
        # Calculate percentages and averages
        for position in self.positions:
            stats = self.stats[position]
            if stats['hands'] == 0:
                continue
                
            stats['vpip'] = stats['vpip'] / stats['hands'] * 100
            stats['pfr'] = stats['pfr'] / stats['hands'] * 100
            stats['win_rate'] = stats['total_won'] / stats['hands'] * 100
            stats['3bet'] = stats['3bet'] / stats['hands'] * 100
            
            if stats['calls'] > 0:
                stats['aggression_factor'] = stats['bets'] / stats['calls']
            
            if stats['cbet_opportunities'] > 0:
                stats['fold_cbet_flop'] = stats['fold_cbet_flop'] / stats['cbet_opportunities'] * 100
            
            # EV BB/100
            bb = 100  # Base value
            if stats['hands'] > 0:
                stats['ev_bb_100'] = (stats['total_profit'] / bb) / stats['hands'] * 100
        
        return self.stats

class PokerVisualizer:
    def __init__(self, stats):
        self.stats = stats
        self.positions = ['UTG', 'UTG1', 'MP', 'HJ', 'CO', 'BTN', 'SB', 'BB', 'overall']
    
    def plot_win_types(self):
        labels = self.positions
        won_showdown = [self.stats[pos]['won_showdown'] for pos in self.positions]
        won_noshow = [self.stats[pos]['won_noshow'] for pos in self.positions]
        total_won = [self.stats[pos]['total_won'] for pos in self.positions]
        ev_bb = [self.stats[pos]['ev_bb_100'] for pos in self.positions]
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        width = 0.2
        x = range(len(labels))
        
        ax.bar(x, won_showdown, width, label='Won at Showdown', color='red')
        ax.bar([p + width for p in x], won_noshow, width, label='Won Without Showdown', color='yellow')
        ax.bar([p + width*2 for p in x], total_won, width, label='Total Won', color='blue')
        
        # Line plot for EV BB/100
        ax2 = ax.twinx()
        ax2.plot(x, ev_bb, 'g-o', linewidth=2, markersize=8, label='EV BB/100')
        
        ax.set_xticks([p + width for p in x])
        ax.set_xticklabels(labels)
        ax.set_xlabel('Position')
        ax.set_ylabel('Hands Count')
        ax2.set_ylabel('EV BB/100')
        ax.set_title('Win Types and EV by Position')
        
        # Combine legends
        lines, labels = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines + lines2, labels + labels2, loc='upper left')
        
        ax.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        return fig
    
    def export_to_csv(self):
        output = StringIO()
        writer = csv.writer(output)
        
        headers = ['position', 'hands', 'vpip', 'pfr', 'aggression_factor', 
                  'fold_cbet_flop', 'win_rate', '3bet', 'won_showdown', 
                  'won_noshow', 'total_won', 'ev_bb_100', 'total_profit']
        writer.writerow(headers)
        
        for position in self.positions:
            stats = self.stats[position]
            row = [
                position,
                stats['hands'],
                f"{stats['vpip']:.2f}%",
                f"{stats['pfr']:.2f}%",
                f"{stats['aggression_factor']:.2f}",
                f"{stats['fold_cbet_flop']:.2f}%",
                f"{stats['win_rate']:.2f}%",
                f"{stats['3bet']:.2f}%",
                stats['won_showdown'],
                stats['won_noshow'],
                stats['total_won'],
                f"{stats['ev_bb_100']:.2f}",
                stats['total_profit']
            ]
            writer.writerow(row)
        
        return output.getvalue()
        
if __name__ == "__main__":
    main()
