#coding:utf8

import math
import random

from .map import Map
from .ants import (
    Ant,
    ExplorerStrategy,
    RandomStrategy,
    FoodStrategy,
    HillStrategy,
)

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

        self.water_map = None
        self.seen_map = None
        self.visible_map = None
        self.vision_map = None

        self.turn = 0
        self.mx = 0

        self.my_hills = set()
        self.my_ants = dict()

        self.food = set()
        self.occupied = set()

        self.enemy_hills = set()
        self.enemy_ants = set()

        self.received_ants = set()
        self.received_my_hills = set()
        self.received_enemy_hills = set()
        self.received_food = set()
    
        random_ = RandomStrategy(self)
        explorer = ExplorerStrategy(self)
        hill_explo = HillStrategy(self, backup = explorer, refresh = 4)
        food_short = FoodStrategy(self, backup = hill_explo, limit = 10, refresh = 2)
        food_long = FoodStrategy(self, backup = explorer, limit = 50, refresh = 3)
        hill_food = HillStrategy(self, backup = food_long, refresh = 4)

        self.strategies = [
            (1, random_),
            (2, explorer),
            (4, hill_explo),
            (9, food_short),
            (5, hill_food),
        ]

    def init(self):
        random.seed(self.player_seed)
        self.water_map = Map(self.rows, self.cols)
        self.seen_map = Map(self.rows, self.cols)
        
        mx = self.mx = int(math.sqrt(self.viewradius2))
        self.vision_map = Map(mx*2+1, mx*2+1)
        for row in range(-mx, mx+1):
            for col in range(-mx, mx+1):
                if row**2 + col**2 <= self.viewradius2:
                    self.vision_map.set(row+mx, col+mx)

    def clear_temporary_state(self):
        pass

    # Functions for controller

    def turn_begin(self, turn):
        self.turn = turn

    def turn_end(self):
        my_ants = set(self.my_ants)
        dead_ants = my_ants - self.received_ants
        for ant in dead_ants:
            err('deleting ant', ant)
            self.my_ants[ant].delete()

        new_ants = self.received_ants - my_ants
        for row, col in new_ants:
            err('inserting ant', (row, col))
            Ant(self, row, col)

        self.visible_map = Map(self.rows, self.cols)
        for ant in self.my_ants.values():
            row, col = ant.row-self.mx, ant.col-self.mx
            self.visible_map.or_with_offset(self.vision_map, row, col)
        self.seen_map.or_with(self.visible_map)

        #for stride in self.seen_map.strides:
        #    err(''.join(('#' if not cell else '.') for cell in stride))

        invisible = self.my_hills - self.received_my_hills
        for pos in invisible:
            if pos in self.visible_map:
                self.my_hills.remove(pos)
        self.my_hills.update(self.received_my_hills)

        invisible = self.enemy_hills - self.received_enemy_hills
        for pos in invisible:
            if pos in self.visible_map:
                self.enemy_hills.remove(pos)
        self.enemy_hills.update(self.received_enemy_hills)

        invisible = self.food - self.received_food
        for pos in invisible:
            if pos in self.visible_map:
                err('removing food', pos)
                self.food.remove(pos)
        self.food.update(self.received_food)

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
        self.received_enemy_hills.clear()
        self.received_my_hills.clear()
        self.received_food.clear()
        self.occupied.clear()
        self.enemy_ants.clear()

    def set_water(self, row, col):
        self.water_map.set(row, col)

    def set_food(self, row, col):
        self.received_food.add((row, col))

    def set_hill(self, row, col, owner):
        t = (row, col)
        if owner:
            self.received_enemy_hills.add(t)
        else:
            self.received_my_hills.add(t)

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
            
        return not (
            self.water_map.get(row, col) or
            t in self.occupied or
            t in self.my_hills or
            t in self.food
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

    def choose_strategy(self, except_=None):
        if except_:
            strategies = [
                (x, y)
                for x, y in self.strategies
                if not isinstance(y, except_)
            ]
        else:
            strategies = self.strategies

        s = float(sum(x for x, y in strategies))
        c = random.random()
        i = 0
        for x, y in strategies:
            i += x/s
            if c <= i:
                return y

