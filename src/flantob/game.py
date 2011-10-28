#coding:utf8

import collections
import math
import random

from .map import (
    DirectionMap,
    Map,
)
from . import ants

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
        self.hill_guards = dict()
        self.my_ants = dict()

        self.food = set()
        self.occupied = dict()

        self.enemy_hills = set()
        self.enemy_ants = dict()

        self.received_ants = set()
        self.received_my_hills = set()
        self.received_enemy_hills = set()
        self.received_food = set()

        self.food_targeters = dict()
        self.food_maps = dict()

        self.strategies = None

    def init(self):
        random.seed(self.player_seed)
        self.water_map = Map(self.rows, self.cols)
        self.seen_map = Map(self.rows, self.cols)
        
        mx = self.mx = int(math.sqrt(self.viewradius2))
        mx2 = self.mx2 = int(math.ceil(2**0.5*mx))
        ax = self.ax = int(math.sqrt(self.attackradius2))
        ax2 = self.ax2 = int(math.ceil(2**0.5*ax))
        self.vision_map = Map(mx*2+1, mx*2+1)
        for row in range(-mx, mx+1):
            for col in range(-mx, mx+1):
                if row**2 + col**2 <= self.viewradius2:
                    self.vision_map.set(row+mx, col+mx)
        #self.vision_map.debug_print()
    
        rand = ants.RandomStrategy(self)
        explo = ants.ExplorerStrategy(self, refresh = 4)#, limit = mx*2)
        periphery = ants.PeripheryStrategy(self, refresh = 4, offset = 1, limit = mx*2)
        target = ants.TargetFoodStrategy(self)

        hill = ants.HillStrategy(self, refresh = 4, offset = 2)
        hill2 = ants.HillStrategy(self, refresh = 4, offset = 3, limit = mx2)

        guard = ants.MyHillGuardStrategy(self, refresh=5, limit = mx2*3)
        repell = ants.RepellOwnStrategy(self)
        focus = ants.FocusStrategy(self)
        rules = ants.MyHillStrategy(self)

        self.managers_attackers = (
            (10, ants.Manager(
                (0.1, rand),
                (2, target),
                (0.3, explo),
                (0.3, periphery),
                (3, focus),
                (1, hill),
                (0.5, rules),
            )),
        )
        self.managers_explorers = (
            (2, ants.Manager(
                (0.1, rand),
                (2, target),
                (0.5, explo),
                (0.6, periphery),
                (3, focus),
                (0.6, hill2),
                (0.5, rules),
                (0.3, repell),
            )),
            (6, ants.Manager(
                (0.1, rand),
                (2, target),
                (0.6, explo),
                (0.5, periphery),
                (3, focus),
                (0.8, hill2),
                (0.5, rules),
                (0.3, repell),
            )),
        )
        self.manager_defender = ants.Manager(
            (0.1, rand),
            (2, target),
            (0.3, guard),
            (1, focus),
            (1.5, rules),
        )

    def clear_temporary_state(self):
        pass

    # Functions for controller

    def turn_begin(self, turn):
        self.turn = turn
        #err('turn', turn)

    def turn_end(self):
        my_ants = set(self.my_ants)
        dead_ants = my_ants - self.received_ants
        for ant in dead_ants:
            #err('deleting ant', ant)
            ant = self.my_ants.pop(ant)
            hill = ant.hill
            if hill and hill in self.hill_guards:
                self.hill_guards[hill] -= 1
            if ant.target:
                del self.food_targeters[ant.target]

        new_ants = self.received_ants - my_ants
        for row, col in new_ants:
            #err('inserting ant', (row, col))
            ant = ants.Ant(self, row, col)
            self.set_manager(ant)
            self.my_ants[(row, col)] = ant

        self.visible_map = Map(self.rows, self.cols)
        for ant in self.my_ants.values():
            row, col = ant.row-self.mx, ant.col-self.mx
            self.visible_map.or_with_offset(self.vision_map, row, col)
        self.seen_map.or_with(self.visible_map)
        #err('visible map')
        #self.visible_map.debug_print()
        #err('seen map')
        #self.seen_map.debug_print()

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

        if self.my_hills:
            invisible = self.food - self.received_food
            for pos in invisible:
                if pos in self.visible_map:
                    #err('removing food', pos)
                    self.food.remove(pos)
                    targeter = self.food_targeters.pop(pos, None)
                    if targeter:
                        targeter.target = None
            self.food.update(self.received_food)

            to_regen = sorted(
                (
                    (target, age)
                    for target, (_, age) in self.food_maps.items()
                    if target in self.food_targeters
                ),
                key = lambda x: x[1],
            )
            if to_regen:
                target, age = to_regen[0]
                #err('has', len(to_regen), 'maps, regen map for food at', target, 'created', self.turn-age, 'turns ago')
                food_map = DirectionMap((target,), self.water_map.direction_map_init(), self.mx2*2)
                self.food_maps[target] = food_map, self.turn

            for target in self.food:
                self.check_food(target)

        for ant in self.my_ants.values():
            ant.make_turn()

        new_ants = dict()
        for ant in self.my_ants.values():
            pos, direction = ant.considered_position, ant.considered_direction
            new_ants[pos] = ant
            if ant.i_wont_move:
                continue
            #err((ant.row,ant.col), '→', pos, 'dir', direction, DIR_N2C[direction])
            print('o %s %s %s' % (ant.row, ant.col, DIR_N2C[direction]))
            ant.row, ant.col = pos
        assert len(self.my_ants) == len(new_ants)
        self.my_ants = new_ants

        print('go')

        self.received_ants.clear()
        self.received_enemy_hills.clear()
        self.received_my_hills.clear()
        self.received_food.clear()
        self.enemy_ants.clear()
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
            self.enemy_ants[t] = owner
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

    def distance_straight(self, pos1, pos2, square = False):
        row1, col1 = pos1
        row2, col2 = pos2
        col1 = abs(col1 - col2)
        row1 = abs(row1 - row2)
        if square:
            return col1 + row1
        else:
            return math.sqrt(min(row1, self.rows - row1)**2 + min(col1, self.cols - col1)**2)

    def set_manager(self, ant):
        pos = ant.row, ant.col
        may_be_defender = False
        if self.turn < 41:
            manager_list = self.managers_explorers
        else:
            manager_list = self.managers_explorers + self.managers_attackers
            if self.my_hills and pos in self.my_hills and self.hill_guards.get(pos, 0) < 4:
                may_be_defender = True
                manager_list += ((sum(x for x, y in manager_list), self.manager_defender),)

        s = float(sum(x for x, y in manager_list))
        c = random.random()
        i = 0
        for x, manager in manager_list:
            i += x/s
            if c <= i:
                break

        if may_be_defender and manager == self.manager_defender:
            self.hill_guards[pos] = self.hill_guards.get(pos, 0) + 1
            ant.hill = pos

        ant.manager = manager

    def get_food_map(self, target, regen = False):
        food_map = self.food_maps.get(target)
        if regen and food_map:
            if food_map[1] != self.turn:
                food_map = None

        if food_map:
            #err('map to', target, 'is', self.turn-food_map[1], 'turns old')
            return food_map[0]

        food_map = DirectionMap((target,), self.water_map.direction_map_init(), self.mx2*2)
        self.food_maps[target] = food_map, self.turn
        return food_map

    def check_food(self, target):
        food_map = self.get_food_map(target)

        #err('checking ants for', target)
        original = possible_targeter = self.food_targeters.get(target)
        distance = 0
        if possible_targeter:
            distance = food_map.get_pos((possible_targeter.row, possible_targeter.col))
            if distance < 0:
                possible_targeter = None
                distance = 0

        for pos, ant in self.my_ants.items():
            if ant == possible_targeter:
                continue

            tmp_distance = food_map.get_pos(pos)
            if tmp_distance < 0 or distance and tmp_distance >= distance:
                continue

            if ant.target:
                current_distance = self.food_maps[ant.target][0].get_pos((ant.row, ant.col))
                if current_distance <= tmp_distance:
                    continue
            distance = tmp_distance
            possible_targeter = ant

        ant = possible_targeter
        if not ant:
            return

        if ant == original:
            return

        if ant.target and ant.target != target:
            del self.food_targeters[ant.target]

        if original:
            del self.food_targeters[original.target]
            original.target = None

        ant.target = target
        self.food_targeters[target] = ant
        #err('ant', (ant.row, ant.col), 'goes to', target)
        #err('food map looks like this:')
        #food_map.debug_print()

    def vector_ants(self, apos, ants, limit2=None, normal_output=False, exclude=None):
        gr = self.rows
        gc = self.cols
        gr2 = gr / 2
        gc2 = gc/ 2
        ra, ca = apos
        for pos, ant in ants:
            if ant == exclude:
                continue
            ir, ic = pos

            ir -= ra
            if abs(ir) > gr2:
                if ir > 0:
                    ir -= gr
                else:
                    ir += gr

            ic -= ca
            if abs(ic) > gc2:
                if ic > 0:
                    ic -= gc
                else:
                    ic += gc

            distance = ir**2 + ic**2
            if limit2 and distance > limit2:
                continue

            if normal_output:
                yield (ir, ic), ant
            else:
                yield ir, ic, distance, ant

