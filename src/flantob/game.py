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
        self.candidates = dict()
        self.occupied = set()

        self.enemy_hills = set()
        self.enemy_ants = set()

        self.received_ants = set()
        self.received_my_hills = set()
        self.received_enemy_hills = set()
        self.received_food = set()

        self.strategies = None

    def init(self):
        random.seed(self.player_seed)
        self.water_map = Map(self.rows, self.cols)
        self.seen_map = Map(self.rows, self.cols)
        
        mx = self.mx = int(math.sqrt(self.viewradius2))
        self.ax = int(math.sqrt(self.attackradius2))
        self.vision_map = Map(mx*2+1, mx*2+1)
        for row in range(-mx, mx+1):
            for col in range(-mx, mx+1):
                if row**2 + col**2 <= self.viewradius2:
                    self.vision_map.set(row+mx, col+mx)
        #self.vision_map.debug_print()
    
        rand = RandomStrategy(self)
        explo = ExplorerStrategy(self)
        mx2 = int(math.ceil(2**0.5*mx))

        food = FoodStrategy(self, limit = mx2, refresh = 3)
        hill = HillStrategy(self, refresh = mx/2)

        self.strategies = [
            (2, (
                (1, food),
                (0.5, explo),
                (0.1, hill),
            )),
            (2, (
                (0.5, food),
                (0.6, explo),
                (1, hill),
            )),
        ]

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
                #err('removing food', pos)
                self.food.remove(pos)
        self.food.update(self.received_food)

        for ant in sorted(self.my_ants.values(), key=lambda x: random.random()):
            ant.make_turn()

        candidates = sorted(
            (
                (pos, tuple(sorted(cs, key=lambda x:x[0], reverse=True)))
                for pos, cs in self.candidates.items()
            ),
            key=lambda x:x[1][0][0], reverse=True
        )

        moved = set() 
        new_ants = dict()
        for pos, cs in candidates:
            for _, ant, direction in cs:
                if ant in moved:
                    continue
                if direction == -1:
                    err('not moving', pos)
                else:
                    del self.my_ants[(ant.row, ant.col)]
                    err((ant.row,ant.col), '→', pos, 'dir', direction, DIR_N2C[direction])
                    print('o %s %s %s' % (ant.row, ant.col, DIR_N2C[direction]))
                    ant.row, ant.col = pos
                    new_ants[pos] = ant
                moved.add(ant)
                break
        self.my_ants.update(new_ants)

        print('go')

        self.received_ants.clear()
        self.received_enemy_hills.clear()
        self.received_my_hills.clear()
        self.received_food.clear()
        self.enemy_ants.clear()
        self.candidates.clear()
        self.occupied.clear()

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

    def distance_straight(self, pos1, pos2):
        row1, col1 = pos1
        row2, col2 = pos2
        col1 -= col2
        row1 -= row2
        return math.sqrt(min(row1, self.rows - abs(row1))**2 + min(col1, self.cols - abs(col1))**2)

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

