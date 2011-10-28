#coding:utf8

import collections
import math
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

class MyHillStrategy(Strategy):
    def instruct_ant(self, ant):
        if (ant.row, ant.col) in self.game.my_hills:
            for direction in range(4):
                yield 9999, direction
        else:
            for direction in range(4):
                pos = self.game.translate(direction, ant.row, ant.col)
                if pos in self.game.my_hills:
                    yield -1, direction

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
        self.refresh = refresh or self.game.mx
        self.offset = offset

    def map_prefill(self):
        raise NotImplementedError

    def map_init(self):
        raise NotImplementedError

    def instruct_ant(self, ant):
        if not self.direction_map or self.last_gen < self.game.turn and not (self.game.turn + self.offset)%self.refresh:
            self.last_gen = self.game.turn
            self.direction_map = DirectionMap(self.map_prefill(), init = self.map_init(), limit = self.limit)
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
    def map_prefill(self):
        return self.game.visible_map.direction_map_edge_prefill()

    def map_init(self):
        return [
            [
                (-2 if (cell1 == -1 or cell2 == -2) else -1)
                for cell1, cell2 in zip(row1, row2)
            ]
            for row1, row2 in zip(self.game.visible_map.strides, self.game.water_map.strides)
        ]

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
        if value <= 4:
            return 0
        return value - 4

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

class FocusStrategy(Strategy):
    def instruct_ant(self, ant):
        search_radius = self.game.attackradius2 * 9
        attack_radius = self.game.attackradius2
        arow, acol = ant.row, ant.col
        apos = (arow, acol)
        all_enemy_ants_nearby = list(self.game.vector_ants(apos, self.game.enemy_ants.items(), search_radius, True))
        if not all_enemy_ants_nearby:
            return
        #err(len(all_enemy_ants_nearby), 'enemies nearby ant', apos)
        all_my_ants_nearby = list(self.game.vector_ants(apos, ((pos, 0) for pos in self.game.my_ants), search_radius, True))
        offsets = ((0, -1, 0), (1, 0, 1), (2, 1, 0), (3, 0, -1)) 
        for my_direction, my_or, my_oc in offsets:
            my_apos = (my_or, my_oc)
            kills_enemy, kills_self = False, False
            kills_count = 0
            for enemy_direction, enemy_or, enemy_oc in offsets:
                enemy_or-= my_or
                enemy_oc-= my_oc
                all_ants = [
                    x
                    for y in (
                        (
                            ((row+enemy_or, col+enemy_oc), owner)
                            for (row, col), owner in all_enemy_ants_nearby
                        ),
                        all_my_ants_nearby,
                    )
                    for x in y
                ]
                #err(apos, my_direction, enemy_direction, enemy_or, enemy_oc, all_ants)
                my_enemies = list(self.game.vector_ants((0, 0), all_ants, attack_radius, True, 0))
                if not my_enemies:
                    continue
                min_enemy_weakness = min(
                    len(list(self.game.vector_ants(pos, all_ants, attack_radius, False, ant)))
                    for pos, ant in my_enemies
                )
                #err(len(my_enemies), 'possible enemies around ant', apos, 'with minimal weakness', min_enemy_weakness)
                if min_enemy_weakness > len(my_enemies):
                    kills_enemy = True
                    kills_count += 1
                else:
                    kills_self = True
                    break

            if kills_self:
                #err('if ant', apos, 'goes to direction', my_direction, 'it may get killed, fleeing!')
                yield -1, my_direction
            elif kills_enemy:
                #err('if ant', apos, 'goes to direction', my_direction, 'it may kill something, CHAAARGE!')
                yield kills_count*0.25, my_direction

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

            #if ic < 0:
            #    d1 += 1
            #else:
            #    d3 += 1

            #if ir < 0:
            #    d2 += 1
            #else:
            #    d0 += 1

            count += 1

        if count:
            count = float(count)
            yield d0/count, 0
            yield d1/count, 1
            yield d2/count, 2
            yield d3/count, 3

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

        self.i_wont_move = False
        self.considered_moves = None
        self.next_consideration = None

        self.considered_direction = None
        self.considered_position = None
        self.confidence = None

    def make_turn(self):
        assert self.strategy

        self.i_wont_move = False

        directions = {0:0, 1:0, 2:0, 3:0}
        sum_weight = 0
        for weight, strategy in self.strategy:
            for confidence, direction in strategy.instruct_ant(self):
                sum_weight += weight
                confidence *= weight
                directions[direction] += confidence

        #err('for ant @', (self.row, self.col), directions)

        self.considered_moves = list(sorted(
            directions.items(),
            key = lambda x: x[1],
            reverse = True,
        ))

        self.next_consideration = 0
        self.reconsider_move()

    def reconsider_move(self):
        while True:
            if self.next_consideration >= len(self.considered_moves):
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

