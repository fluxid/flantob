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

class DirectedStrategy(Strategy):
    def __init__(self, game, backup = None, limit = None, refresh = None, *args, **kwargs):
        super().__init__(game, *args, **kwargs)
        self.last_gen = game.turn
        self.backup_strategy = backup or RandomStrategy(game)
        self.direction_map = None
        self.limit = limit
        self.refresh = refresh or self.game.mx

    def map_prefill(self):
        raise NotImplementedError

    def map_init(self):
        raise NotImplementedError

    def instruct_ant(self, ant):
        if not self.direction_map or (self.game.turn - self.last_gen > self.refresh):
            self.last_gen = self.game.turn
            self.direction_map = DirectionMap(self.map_prefill(), init = self.map_init(), limit = self.limit)
            #err(self, self.limit)
            #self.direction_map.debug_print()
            if not self.direction_map.ready:
                self.backup_strategy.instruct_ant(ant)
                return
        elif not self.direction_map.ready:
            self.direction_map.resume()
            self.backup_strategy.instruct_ant(ant)
            return

        row, col = ant.row, ant.col
        value = self.direction_map.get_pos((row, col))
        if value == -2:
            self.backup_strategy.instruct_ant(ant)
            return

        translated = [
            (a, b, c)
            #(a + (random.random()*1.5-0.75), b, c)
            for a, b, c in (
                (self.direction_map.get_pos(j), i, j)
                for i, j in (
                    (k, self.game.translate(k, row, col))
                    for k in range(4)
                )
                if self.game.can_enter(j)
            )
            if a >= 0
        ]
        if not translated:
            self.backup_strategy.instruct_ant(ant)
            return
        random.shuffle(translated)
        translated.sort()
        value, direction, pos = translated[0]
        #if value == -1:
        #    self.backup_strategy.instruct_ant(ant)
        #    return
        ant.move(direction, pos)

class ExplorerStrategy(DirectedStrategy):
    def map_prefill(self):
        return self.game.seen_map.direction_map_edge_prefill()

    def map_init(self):
        return (
            (
                (-2 if (not cell1 or cell2) else -1)
                for cell1, cell2 in zip(row1, row2)
            )
            for row1, row2 in zip(self.game.seen_map.strides, self.game.water_map.strides)
        )

class FoodStrategy(DirectedStrategy):
    def map_prefill(self):
        return self.game.food

    def map_init(self):
        return self.game.water_map.direction_map_init()

class HillStrategy(DirectedStrategy):
    def map_prefill(self):
        return self.game.enemy_hills

    def map_init(self):
        return self.game.water_map.direction_map_init()

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
        #err(pos, new_pos)
        self.game.my_ants[new_pos] = self

