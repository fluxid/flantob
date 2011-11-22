#coding:utf8

import re
import sys
from time import sleep

from .game import Game

RE_SP = re.compile('\s+')


class Controller:
    def __init__(self):
        self.game = None
        self.state = None

    def run(self):
        self.game = Game()

        sdict = self.states.get('begin')
        while True:
            try:
                line = sys.stdin.readline()
            except EOFError:
                break
            line = line.strip()
            if not line:
                continue
            #err(line)
            args = RE_SP.split(line)
            command = args.pop(0)

            command = sdict.get(command)
            if not command:
                continue

            state = command(self, *args)
            sys.stdout.flush()
            if state == 'quit':
                #err('quitting')
                sys.exit(0)
                break
            if state:
                sdict = self.states.get(state)
                if sdict is None:
                    raise RuntimeError('Unknown state: %s' % state)

    def action_begin_loadtime(self, loadtime):
        self.game.loadtime = int(loadtime)

    def action_begin_turntime(self, loadtime):
        self.game.turntime = int(loadtime)

    def action_begin_rows(self, rows):
        self.game.rows = int(rows)

    def action_begin_cols(self, cols):
        self.game.cols = int(cols)

    def action_begin_turns(self, turns):
        self.game.turns = int(turns)

    def action_begin_viewradius2(self, viewradius2):
        self.game.viewradius2 = int(viewradius2)

    def action_begin_attackradius2(self, attackradius2):
        self.game.attackradius2 = int(attackradius2)

    def action_begin_spawnradius2(self, spawnradius2):
        self.game.spawnradius2 = int(spawnradius2)

    def action_begin_player_seed(self, player_seed):
        self.game.player_seed = int(player_seed)

    def action_begin_ready(self):
        self.game.init()
        print('go')
        return 'turns'


    def action_turns_turn(self, turn):
        self.game.turn_begin(int(turn))
        return 'turn'

    def action_turns_end(self):
        return 'end'


    def action_turn_w(self, row, col):
        self.game.set_water(int(row), int(col))
 
    def action_turn_f(self, row, col):
        self.game.set_food(int(row), int(col))
 
    def action_turn_h(self, row, col, owner):
        self.game.set_hill(int(row), int(col), int(owner))
 
    def action_turn_a(self, row, col, owner):
        self.game.set_ant(int(row), int(col), int(owner))
 
    def action_turn_d(self, row, col, owner):
        self.game.set_dead_ant(int(row), int(col), int(owner))
 
    def action_turn_go(self):
        #with timer('turn'):
        self.game.turn_end()
        return 'turns'

 
    def action_end_go(self):
        return 'quit'


    states = dict(
        begin = dict(
            loadtime = action_begin_loadtime,
            turntime = action_begin_turntime,
            rows = action_begin_rows,
            cols = action_begin_cols,
            turns = action_begin_turns,
            viewradius2 = action_begin_viewradius2,
            attackradius2 = action_begin_attackradius2,
            spawnradius2 = action_begin_spawnradius2,
            player_seed = action_begin_player_seed,
            ready = action_begin_ready,
        ),
        turns = dict(
            turn = action_turns_turn,
            end = action_turns_end,
        ),
        turn = dict(
            w = action_turn_w,
            f = action_turn_f,
            h = action_turn_h,
            a = action_turn_a,
            d = action_turn_d,
            go = action_turn_go,
        ),
        end = dict(
            go = action_end_go,
        ),
    )

