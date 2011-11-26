#coding:utf8

import collections
import math
import random

from . import cstuff
from .map import DirectionMap, direction_map_edge_prefill

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

class SimpleRulesStrategy(Strategy):
    def instruct_ant(self, ant):
        if (ant.row, ant.col) in self.game.my_hills:
            for direction in range(4):
                pos = self.game.translate(direction, ant.row, ant.col)
                counter = 0
                row2, col2 = pos
                for direction2 in range(4):
                    pos2 = self.game.translate(direction2, row2, col2)
                    if pos2 in self.game.my_hills or self.game.water_map.get(*pos2):
                        counter += 1
                if counter == 4:
                    # Don't go into that fucking hole by the hill in maze map!
                    yield -1, direction
                else:
                    yield 1, direction
        else:
            for direction in range(4):
                pos = self.game.translate(direction, ant.row, ant.col)
                if pos in self.game.my_hills:
                    yield -10, direction

class DirectedStrategy(Strategy):
    inverted = False
    def hit_water(self, ant, direction):
        pass

    def get_directions(self, ant, direction_map):
        row, col = ant.row, ant.col
        value = direction_map.get_pos((row, col))
        queue = collections.deque()

        for k in range(4):
            pos = self.game.translate(k, row, col)
            value2 = direction_map.get_pos(pos)
            if value2 < 0:
                continue
            if self.game.water_map.get(pos):
                self.hit_water(ant, direction_map)
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

        inverted = self.inverted

        for value2, direction in queue:
            if not inverted and (value > value2) or inverted and (value2 > value):
                yield 1, direction
            elif value == value2:
                yield 0.5, direction
            else:
                yield 0.1, direction

class AutoDirectedStrategy(DirectedStrategy):
    def __init__(self, game, backup = None, limit = None, refresh = None, offset = 0, *args, **kwargs):
        super().__init__(game, *args, **kwargs)
        self.last_gen = game.turn
        self.direction_map = None
        self.limit = limit
        if refresh and refresh < 2:
            refresh = None
        self.refresh = refresh
        self.offset = offset

    def map_preinit(self):
        pass

    def map_prefill(self):
        raise NotImplementedError

    def map_init(self):
        raise NotImplementedError

    def make_map(self):
        self.map_preinit()
        self.direction_map = DirectionMap(self.map_prefill(), init = self.map_init(), limit = self.limit)

    def instruct_ant(self, ant):
        if not self.direction_map or self.last_gen < self.game.turn and (not self.refresh or (self.game.turn + self.offset)%self.refresh):
            self.last_gen = self.game.turn
            self.make_map()
            #err(self, self.limit)
            #self.direction_map.debug_print()
        elif not self.direction_map.ready:
            self.direction_map.resume()
        #err(self)
        #self.direction_map.debug_print()

        return self.get_directions(ant, self.direction_map)

class ExplorerStrategy(AutoDirectedStrategy):
    def map_prefill(self):
        return self.game.seen_map.direction_map_edge_prefill()

    def map_init(self):
        return [
            [
                (-2 if (cell1 == -1 or cell2 == -2) else -1)
                for cell1, cell2 in zip(row1, row2)
            ]
            for row1, row2 in zip(self.game.seen_map.strides, self.game.water_map.strides)
        ]

class PeripheryStrategy(AutoDirectedStrategy):
    def map_preinit(self):
        gomap = self.gomap = cstuff.find_low_density_blobs(self.game.my_ants, self.game.water_map.strides)
        #print('v setFillColor 255 255 255 0.3')
        #for row, stride in enumerate(gomap):
        #    for col, value in enumerate(stride):
        #        if value == -1:
        #            print('v tile %s %s'%(row, col))

    def map_prefill(self):
        return direction_map_edge_prefill(self.gomap)
        #return self.game.visible_map.direction_map_edge_prefill()

    def map_init(self):
        return [
            [
                (-2 if (cell1 == -1 or cell2 == -2) else -1)
                for cell1, cell2 in zip(row1, row2)
            ]
            for row1, row2 in zip(self.gomap, self.game.water_map.strides)
        ]

    def make_map(self):
        r = super().make_map()
        #gc = None
        #def ccc(cc):
        #    nonlocal gc
        #    if cc != gc:
        #        print('v setFillColor ' + cc)
        #        gc = cc
        #for row, stride in enumerate(self.direction_map.strides):
        #    for col, value in enumerate(stride):
        #        if value == -1:
        #            continue
        #        elif value == -2:
        #            continue
        #            ccc('0 0 255 0.3')
        #        else:
        #            x = 1.0 - (value/10.0)
        #            if x<=0:
        #                continue
        #            ccc('255 255 255 %.2f'%x)
        #        print('v tile %s %s'%(row, col))
        return r

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

class MyHillGuardStrategy(AutoDirectedStrategy):
    def get_pos(self, pos, direction_map):
        value = direction_map.get_pos(pos)
        if value <= 2:
            return 2 - value
        return value - 2

    def map_prefill(self):
        return self.game.my_hills

    def map_init(self):
        return self.game.water_map.direction_map_init()

class TargetFoodStrategy(AutoDirectedStrategy):
    def hit_water(self, ant, direction):
        #err('ant', (ant.row, ant.col), 'hit water when trying to reach', ant.target, 'reloading map')
        self.game.get_food_map(ant.target, True)

    def instruct_ant(self, ant):
        target = ant.target
        if not target:
            return ()
        direction_map = self.game.food_maps[target][0]
        if ant.turns_left:
            ant.turns_left -= 1
            if not ant.turns_left:
                #err('ant', (ant.row, ant.col), 'has not runs left to reach target', target)
                ant.target = None
                del self.game.food_targeters[target]

        if direction_map.get_pos((ant.row, ant.col)) < 0:
            #err('ant', (ant.row, ant.col), 'is out of current direction map to', target)
            ant.target = None
            del self.game.food_targeters[target]
            return ()
        return self.get_directions(ant, direction_map)

class RepellOwnStrategy(Strategy):
    def instruct_ant(self, ant):
        d0, d1, d2, d3 = 0, 0, 0, 0
        limit = float(self.game.viewradius2)
        count = 0
        for ir, ic, d, ant in self.game.vector_ants((ant.row, ant.col), self.game.my_ants.items(), limit):
            d = (limit - d)/limit
            ir*=d
            ic*=d

            if ic < 0:
                d1 -= ic
            else:
                d3 += ic

            if ir < 0:
                d2 -= ir
            else:
                d0 += ir

            count += 1

        if count:
            count = float(count)
            yield d0/count, 0
            yield d1/count, 1
            yield d2/count, 2
            yield d3/count, 3

class GroupOwnStrategy(Strategy):
    def instruct_ant(self, ant):
        d0, d1, d2, d3 = 0, 0, 0, 0
        limit = float(self.game.viewradius2)
        count = 0
        for ir, ic, d, ant in self.game.vector_ants((ant.row, ant.col), self.game.my_ants.items(), limit):
            d = (limit - d)/limit
            ir*=d
            ic*=d

            if ic < 0:
                d1 += ic
            else:
                d3 -= ic

            if ir < 0:
                d2 += ir
            else:
                d0 -= ir

            count += 1

        if count:
            count = float(count)
            yield d0/count, 0
            yield d1/count, 1
            yield d2/count, 2
            yield d3/count, 3

class Manager:
    def __init__(self, name, *strategies):
        self.strategies = strategies
        self.name = name

    def get_moves(self, ant):
        directions = {0:0, 1:0, 2:0, 3:0}
        sum_weight = 0
        for weight, strategy in self.strategies:
            for confidence, direction in strategy.instruct_ant(ant):
                sum_weight += weight
                confidence *= weight
                directions[direction] += confidence

        #err('for ant @', (ant.row, ant.col), directions)

        return directions

class Ant:
    def __init__(self, game, row, col):
        self.game = game
        self.row = row
        self.col = col
        self.manager = None
 
        pos = self.row, self.col
        self.target = None
        self.turns_left = None
        self.hill = None

        self.i_wont_move = False
        self.considered_hold = False
        self.considered_moves_dict = None
        self.considered_moves = None
        self.next_consideration = None

        self.considered_direction = None
        self.considered_position = None
        self.confidence = None
        self.enemy_checks = 0

    def calculate_moves(self):
        self.enemy_checks = 0
        self.considered_hold = False
        self.considered_moves_dict = self.manager.get_moves(self)

    def consider_moves(self):
        self.i_wont_move = False
        self.next_consideration = 0

        minimum = min(self.considered_moves_dict.values())
        if minimum < 0:
            self.considered_moves = list(sorted(
                (
                    (direction, value-minimum)
                    for direction, value in self.considered_moves_dict.items()
                ),
                key = lambda x: x[1],
                reverse = True,
            ))
        else:
            self.considered_moves = list(sorted(
                self.considered_moves_dict.items(),
                key = lambda x: x[1],
                reverse = True,
            ))
        self.reconsider_move()

    def reconsider_move(self):
        while True:
            if self.considered_hold or self.next_consideration >= len(self.considered_moves):
                self.considered_direction, self.considered_position, self.confidence = -1, (self.row, self.col), 0
                self.i_wont_move = True
                pos = self.row, self.col
                ant = self.game.occupied.pop(pos, None)
                self.game.occupied[pos] = self
                if ant and not ant == self:
                    ant.reconsider_move()
                return

            direction, confidence = self.considered_moves[self.next_consideration]
            self.next_consideration += 1
            pos = self.game.translate(direction, self.row, self.col)
            if not self.game.can_enter(pos):
                continue
            self.considered_direction, self.considered_position, self.confidence = direction, pos, confidence
            ant = self.game.occupied.get(pos)
            if ant and not ant == self:
                if ant.confidence > confidence or ant.i_wont_move:
                    continue
                self.game.occupied[pos] = self
                ant.reconsider_move()
                return
            self.game.occupied[pos] = self
            return

