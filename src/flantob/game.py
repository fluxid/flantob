#coding:utf8

import random

from .map import Map
from .ants import Ant

DIR_N2C = {
    0:'n',
    1:'e',
    2:'s',
    3:'w',
}

class Game:
    def __init__(self):
        self.loadtime = None
        self.turntime = None
        self.rows = None
        self.cols = None
        self.turns = None
        self.viewradius2 = None
        self.attackradius2 = None
        self.spawnradius2 = None
        self.player_seed = None

        self.map_ = None

        self.turn = 0

        self.my_hills = dict()
        self.my_ants = dict()

        self.food = set()
        self.occupied = set()

        self.enemy_hills = set()
        self.enemy_ants = set()

        self.received_ants = set()

    def init(self):
        random.seed(self.player_seed)
        self.map_ = Map(self.rows, self.cols)

    def clear_temporary_state(self):
        pass

    # Functions for controller

    def turn_begin(self, turn):
        self.turn = turn

    def turn_end(self):
        my_ants = set(self.my_ants)
        dead_ants = my_ants - self.received_ants
        for ant in dead_ants:
            err('deleting', ant)
            self.my_ants[ant].delete()

        new_ants = self.received_ants - my_ants
        for row, col in new_ants:
            err('inserting', (row, col))
            Ant(self, row, col)

        for ant in self.my_ants.values():
            move = ant.make_turn()
            if move:
                row, col, direction = move
                print('o %s %s %s' % (row, col, DIR_N2C[direction]))

        print('go')

        my_old_ants = self.my_ants
        self.my_ants = dict()
        for ant in my_old_ants.values():
            ant.finish_turn()

        self.received_ants.clear()
        self.occupied.clear()
        self.enemy_ants.clear()
        self.food.clear()

    def set_water(self, row, col):
        self.map_.set_water(row, col)

    def set_food(self, row, col):
        self.food.add((row, col))

    def set_hill(self, row, col, owner):
        t = (row, col)
        if owner:
            self.enemy_hill.add(t)
        else:
            self.my_hills[t] = True # TODO

    def set_ant(self, row, col, owner):
        t = (row, col)
        if owner:
            self.enemy_ants.add(t)
        else:
            self.received_ants.add(t)

    def set_dead_ant(self, row, col, owner):
        pass

    # utils

    def can_enter(self, row, col=None):
        if col is None:
            t = row
            row, col = t
        else:
            t = (row, col)
            
        return (
            self.map_.can_enter(row, col) and
            t not in self.occupied and
            t not in self.my_hills and
            t not in self.food
        )

    def translate(self, direction, row, col=None):
        if col is None:
            row, col = row
            
        if direction == 0:
            row = (row-1) % self.rows
        elif direction == 1:
            col = (col+1) % self.cols
        elif direction == 2:
            row = (row+1) % self.rows
        elif direction == 3:
            col = (col-1) % self.cols
        return (row, col)

    def random_translate(self, row, col=None):
        if col is None:
            row, col = row
        
        translated = [
            (i, j)
            for i, j in (
                (k, self.translate(k, row, col))
                for k in range(4)
            )
            if self.can_enter(j)
        ]

        if translated:
            return random.choice(translated)

        if self.can_enter(row, col):
            # Don't move at all
            return -1, (row, col)

        # Fuckup warning: we may loose ant or collide it with other...
        direction = random.randint(0, 3)
        return direction, self.translate(direction, row, col)

