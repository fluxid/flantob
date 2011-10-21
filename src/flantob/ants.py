#coding:utf8

import random

class Strategy:
    def __init__(self):
        pass

    def instruct_ant(self, ant):
        raise NotImplementedError

    def bury_ant(self, ant):
        pass

class RandomStrategy(Strategy):
    def instruct_ant(self, ant):
        row, col = ant.row, ant.col
        direction, pos = ant.game.random_translate(row, col)
        ant.move(direction, pos)

random_strategy = RandomStrategy()

class Ant:
    def __init__(self, game, row, col):
        self.game = game
        self.row = row
        self.col = col
        self.strategy = random_strategy 
 
        pos = self.row, self.col
        self.game.my_ants[pos] = self

        self.new_pos = None

    def make_turn(self):
        self.strategy.instruct_ant(self)
        if self.direction != -1:
            return self.row, self.col, self.direction

    def move(self, direction, pos):
        self.new_pos = pos
        self.direction = direction
        self.game.occupied.add(pos)

    def delete(self):
        pos = self.row, self.col
        self.strategy.bury_ant(self)
        self.game.my_ants.pop(pos, None)

    def finish_turn(self):
        pos = self.row, self.col
        new_pos = self.new_pos
        self.row, self.col = self.new_pos
        err(pos, new_pos)
        self.game.my_ants[new_pos] = self

