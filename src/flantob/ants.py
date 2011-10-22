#coding:utf8

import random

from .map import DirectionMap

class Strategy:
    def __init__(self, game):
        self.game = game

    def instruct_ant(self, ant):
        raise NotImplementedError

    def bury_ant(self, ant):
        pass

class RandomStrategy(Strategy):
    def instruct_ant(self, ant):
        row, col = ant.row, ant.col
        direction, pos = self.game.random_translate(row, col)
        ant.move(direction, pos)

class ExplorerStrategy(Strategy):
    def __init__(self, game, *args, **kwargs):
        super().__init__(game, *args, **kwargs)
        self.last_gen = game.turn
        self.backup_strategy = RandomStrategy(game)
        self.direction_map = None

    def prefill(self):
        strides = self.game.seen_map.strides
        last_stride = strides[-1]
        for row, stride in enumerate(strides):
            last_cell = stride[-1]
            for col, cell in enumerate(stride):
                if cell and not last_cell:
                    yield (row, col)
                elif not cell and last_cell:
                    yield (row, col-1)
                else:
                    last_cell = last_stride[col]
                    if cell and not last_cell:
                        yield (row, col)
                    elif not cell and last_cell:
                        yield (row-1, col)
                last_cell = cell
            last_stride = stride

    def orinit(self):
        return (
            (
                (-2 if (not cell1 or cell2) else -1)
                for cell1, cell2 in zip(row1, row2)
            )
            for row1, row2 in zip(self.game.seen_map.strides, self.game.water_map.strides)
        )

    def instruct_ant(self, ant):
        if not self.direction_map or (self.game.turn - self.last_gen > self.game.mx):
            self.last_gen = self.game.turn
            #with timer('MAPAAAA'):
            self.direction_map = DirectionMap(self.game, self.prefill(), init = self.orinit())
            if not self.direction_map.ready:
                self.backup_strategy.instruct_ant(ant)
                return
        elif not self.direction_map.ready:
            self.direction_map.resume()
            self.backup_strategy.instruct_ant(ant)
            return

        row, col = ant.row, ant.col
        translated = [
            (self.direction_map.get_pos(j) + (random.random()*1.5-0.75), i, j)
            for i, j in (
                (k, self.game.translate(k, row, col))
                for k in range(4)
            )
            if self.game.can_enter(j)
        ]
        if not translated:
            self.backup_strategy.instruct_ant(ant)
            return
        random.shuffle(translated)
        translated.sort()
        _, direction, pos = translated[0]
        ant.move(direction, pos)

class Ant:
    def __init__(self, game, row, col):
        self.game = game
        self.row = row
        self.col = col
        self.strategy = game.choose_strategy()
 
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

