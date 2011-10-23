#coding:utf8

import collections
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
        elif not self.direction_map.ready:
            self.direction_map.resume()

        row, col = ant.row, ant.col
        value = self.direction_map.get_pos((row, col))
        queue = collections.deque()

        for k in range(4):
            pos = self.game.translate(k, row, col)
            value2 = self.direction_map.get_pos(pos)
            if value2 < 0:
                continue
            queue.append((value2, k))

        if not queue:
            return

        mmin = min(x for x, y in queue)
        mmax = max(x for x, y in queue)
        if value < 0:
            value = mmax
        if mmax == mmin:
            mmax = 1.0
        else:
            mmax = float(mmax - mmin)

        for value2, direction in queue:
            if value > value2:
                yield 1, direction
            elif value == value2:
                yield 0.5, direction
            else:
                yield 0.1, direction

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
        strategy = game.choose_strategy()
        if not isinstance(strategy, (list, tuple)):
            strategy = [(1, strategy)]
        self.strategy = strategy
 
        pos = self.row, self.col
        self.game.my_ants[pos] = self

    def make_turn(self):
        directions = dict()
        sum_weight = 0
        for weight, strategy in self.strategy:
            for confidence, direction in strategy.instruct_ant(self):
                sum_weight += weight
                confidence *= weight
                directions[direction] = directions.get(direction, 0) + confidence

        err('for ant @', (self.row, self.col), directions)

        found = False
        for direction, confidence in directions.items():
            pos = self.game.translate(direction, self.row, self.col)
            if not self.game.can_enter(pos):
                continue
            self.game.candidates.setdefault(pos, []).append((confidence, self, direction))
            found = True

        if not found:
            self.game.candidates.setdefault((self.row, self.col), []).append((999, self, -1))
        
    def delete(self):
        pos = self.row, self.col
        for _, strategy in self.strategy:
            strategy.bury_ant(self)
        self.game.my_ants.pop(pos, None)

