#coding:utf8

import random

from .map import Map

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

    def init(self):
        random.seed(self.player_seed)
        self.map_ = Map(self.rows, self.cols)

    def clear_temporary_state(self):
        pass

    def turn_begin(self, turn):
        self.turn = turn

    def turn_end(self):
        print('go')

    def set_water(self, row, col):
        self.map_.set_water

    def set_food(self, row, col):
        pass

    def set_hill(self, row, col, owner):
        pass

    def set_ant(self, row, col, owner):
        pass

    def set_dead_ant(self, row, col, owner):
        pass

