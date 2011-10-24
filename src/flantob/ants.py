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
        return (
            (random.random(), x)
            for x in range(4)
        )

class DirectedStrategy(Strategy):
    def get_directions(self, ant, direction_map):
        row, col = ant.row, ant.col
        value = direction_map.get_pos((row, col))
        queue = collections.deque()

        for k in range(4):
            pos = self.game.translate(k, row, col)
            value2 = direction_map.get_pos(pos)
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

class AutoDirectedStrategy(DirectedStrategy):
    def __init__(self, game, backup = None, limit = None, refresh = None, offset = 0, *args, **kwargs):
        super().__init__(game, *args, **kwargs)
        #self.last_gen = game.turn
        self.direction_map = None
        self.limit = limit
        self.refresh = refresh or self.game.mx
        self.offset = offset

    def map_prefill(self):
        raise NotImplementedError

    def map_init(self):
        raise NotImplementedError

    def instruct_ant(self, ant):
        if not self.direction_map or not (self.game.turn + self.offset)%self.refresh:
            self.last_gen = self.game.turn
            self.direction_map = DirectionMap(self.map_prefill(), init = self.map_init(), limit = self.limit)
            #err(self, self.limit)
            #self.direction_map.debug_print()
        elif not self.direction_map.ready:
            self.direction_map.resume()

        return self.get_directions(ant, self.direction_map)

class ExplorerStrategy(AutoDirectedStrategy):
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

class PeripheryStrategy(AutoDirectedStrategy):
    def map_prefill(self):
        return self.game.seen_map.direction_map_edge_prefill()

    def map_init(self):
        return (
            (
                (-2 if (not cell1 or cell2) else -1)
                for cell1, cell2 in zip(row1, row2)
            )
            for row1, row2 in zip(self.game.visible_map.strides, self.game.water_map.strides)
        )

class FoodStrategy(AutoDirectedStrategy):
    def map_prefill(self):
        return self.game.food

    def map_init(self):
        return self.game.water_map.direction_map_init()

class HillStrategy(AutoDirectedStrategy):
    def map_prefill(self):
        return self.game.enemy_hills

    def map_init(self):
        return self.game.water_map.direction_map_init()

class TargetStrategy(AutoDirectedStrategy):
    def instruct_ant(self, ant):
        if not ant.target:
            return ()
        if ant.turns_left:
            ant.turns_left -= 1
            if not ant.turns_left:
                err('ant', (ant.row, ant.col), 'has not runs left to reach target', ant.target)
                self.game.remove_target(ant.target)
                return ()
        direction_map = self.game.targets[ant.target][0]
        if direction_map.get_pos((ant.row, ant.col)) < 0:
            err('ant', (ant.row, ant.col), 'is out of current direction map')
            self.game.remove_target(ant.target)
            return ()
        return self.get_directions(ant, direction_map)

class Ant:
    def __init__(self, game, row, col):
        self.game = game
        self.row = row
        self.col = col
        strategy = None
        if not isinstance(strategy, (list, tuple)):
            strategy = [(1, strategy)]
        self.strategy = strategy
 
        pos = self.row, self.col
        self.target = None
        self.turns_left = None
        self.followers = set()

    def make_turn(self):
        assert self.strategy
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

