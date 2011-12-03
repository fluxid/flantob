#coding:utf8

import collections
import math
import random
import time

from . import cstuff
from .map import (
    Map,
    direction_map_edge_prefill,
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

        self.dmap_exploration = None
        self.dmap_periphery = None
        self.dmap_my_hills = None
        self.dmap_enemy_hills = None

        self.area = 1
        self.area_visible = 0

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
        self.cached_dmaps = list()

        self.strategies = None

        self.start_time = None

    def init(self):
        random.seed(self.player_seed)
        self.water_map = Map(self.rows, self.cols)
        self.seen_map = Map(self.rows, self.cols)
        self.area = float(self.rows * self.cols)

        cstuff.init(self.rows, self.cols, self.viewradius2, 12, 0.3)

        self.dmap_exploration = cstuff.DirectionMap()
        self.dmap_periphery = cstuff.DirectionMap()
        self.dmap_my_hills = cstuff.DirectionMap()
        self.dmap_enemy_hills = cstuff.DirectionMap()
        
        mxf = math.sqrt(self.viewradius2)
        mx = self.mx = int(mxf)
        mx2 = self.mx2 = int(math.ceil(2**0.5*mx))
        ax = self.ax = int(math.sqrt(self.attackradius2))
        ax2 = self.ax2 = int(math.ceil(2**0.5*ax))
        self.vision_map = Map(mx*2+1, mx*2+1)
        for row in range(-mx, mx+1):
            for col in range(-mx, mx+1):
                if row**2 + col**2 <= self.viewradius2:
                    self.vision_map.set(row+mx, col+mx)
    
        rand = ants.RandomStrategy(self)
        explo = ants.AutoDirectedStrategy(self, self.dmap_exploration)
        explo2 = ants.AutoDirectedStrategy(self, self.dmap_exploration, limit=mx2)
        periphery = ants.AutoDirectedStrategy(self, self.dmap_periphery)
        target = ants.TargetFoodStrategy(self)

        hill = ants.AutoDirectedStrategy(self, self.dmap_enemy_hills)
        hill2 = ants.AutoDirectedStrategy(self, self.dmap_enemy_hills, limit=mx2)

        guard = ants.MyHillGuardStrategy(self, limit = mx2*3)
        repell = ants.RepellOwnStrategy(self)
        group = ants.GroupOwnStrategy(self)
        rules = ants.SimpleRulesStrategy(self)

        self.managers_attackers = (
            #(5, ants.Manager(
            #    'attacker',
            #    (0.05, rand),
            #    (3, target),
            #    (0.4, explo),
            #    (0.3, periphery),
            #    (1.4, hill),
            #    (1, rules),
            #    (0.1, group),
            #)),
            (11, ants.Manager(
                'attacker',
                (0.05, rand),
                (3, target),
                (0.4, explo),
                (0.3, periphery),
                (1.4, hill),
                (1, rules),
                #(0.1, repell),
            )),
        )
        self.managers_explorers = (
            (8, ants.Manager(
                'explorer2',
                (0.05, rand),
                (3, target),
                (0.5, explo2),
                (0.3, periphery),
                (0.6, hill2),
                (1, rules),
                (0.1, repell),
            )),
        )
        self.manager_defender = ants.Manager(
            'defender',
            (0.05, rand),
            (2, target),
            (0.3, guard),
            (1, rules),
        )

    def clear_temporary_state(self):
        pass

    def turn_begin(self, turn):
        self.turn = turn
        err('turn', turn)

    def time_remaining(self):
        return self.turntime - (time.time() - self.start_time)

    def turn_end(self):
        self.start_time = time.time()

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

        #print('v setFillColor 0 0 0 0.8')
        #for row, stride in enumerate(self.seen_map.strides):
        #    for col, value in enumerate(stride):
        #        if value != -2:
        #            print('v tile %s %s'%(row, col))

        before = len(self.my_hills)
        invisible = self.my_hills - self.received_my_hills
        for pos in invisible:
            if pos in self.visible_map:
                self.my_hills.remove(pos)
        self.my_hills.update(self.received_my_hills)
        lost_all_my_hills = before and not self.my_hills

        invisible = self.enemy_hills - self.received_enemy_hills
        for pos in invisible:
            if pos in self.visible_map:
                self.enemy_hills.remove(pos)
        self.enemy_hills.update(self.received_enemy_hills)

        cstuff.do_ant_stuff(self.my_ants)

        #if self.turns

        self.dmap_exploration.clear()
        self.dmap_exploration.set_walls(self.seen_map.strides, -1)
        self.dmap_exploration.set_walls(self.water_map.strides, -2)
        self.dmap_exploration.fill_near(self.seen_map.direction_map_edge_prefill(), -1) 

        self.dmap_periphery.clear()
        density_map = cstuff.find_low_density_blobs(self.my_ants, self.water_map.strides)
        self.dmap_periphery.set_walls(density_map, -1)
        self.dmap_periphery.set_walls(self.water_map.strides, -2)
        self.dmap_periphery.fill(direction_map_edge_prefill(density_map, self.rows, self.cols), -1) 

        self.dmap_my_hills.clear()
        self.dmap_my_hills.set_walls(self.water_map.strides, -2)
        self.dmap_my_hills.fill(self.my_hills, -1) 

        self.dmap_enemy_hills.clear()
        self.dmap_enemy_hills.set_walls(self.water_map.strides, -2)
        self.dmap_enemy_hills.fill_near(self.enemy_hills, -1) 

        if self.my_hills:
            invisible = self.food - self.received_food
            for pos in invisible:
                if pos in self.visible_map:
                    #err('removing food', pos)
                    self.food.remove(pos)
                    dmap = self.food_maps.pop(pos, None)
                    if dmap:
                        dmap, _ = dmap
                        self.cached_dmaps.append(dmap)
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
                if age != self.turn:
                    #err('has', len(to_regen), 'maps, regen map for food at', target, 'created', self.turn-age, 'turns ago')
                    self.get_food_map(target, True)

            for target in self.food:
                self.check_food(target)
        elif lost_all_my_hills:
            err("I've just lost ALL MY HILLS")

        for ant in self.my_ants.values():
            ant.calculate_moves()

        iterations = 0
        duration = 0
        enemy_cache = dict()
        self.occupied.clear()
        while True:
            ctime = time.time()
            if not self.solve_moves(enemy_cache):
                #err('No more calculations to be made after', iterations, 'iterations')
                break
            duration = max(time.time()-ctime, duration)
            if self.time_remaining() - duration < 0.01: # leave at least 10ms for response and moving ants
                #err('Breaking after', iterations, 'iterations, with max solving time', duration, 'because what is left is', self.time_remaining())
                break
            iterations += 1
            #err('iteration', iterations)

        new_ants = dict()
        for ant in self.my_ants.values():
            pos, direction = ant.considered_position, ant.considered_direction
            new_ants[pos] = ant
            if ant.i_wont_move:
                continue
            #err((ant.row,ant.col), '→', pos, 'dir', direction, DIR_N2C[direction], ant.manager.name, ant.confidence, ant.considered_moves)
            print('o %s %s %s' % (ant.row, ant.col, DIR_N2C[direction]))
            ant.row, ant.col = pos
        #assert len(self.my_ants) == len(new_ants)
        self.my_ants = new_ants

        print('go')

        self.received_ants.clear()
        self.received_enemy_hills.clear()
        self.received_my_hills.clear()
        self.received_food.clear()
        self.enemy_ants.clear()
        self.occupied.clear()

    def solve_moves(self, enemy_cache):
        changes_made = False

        for ant in self.my_ants.values():
            ant.consider_moves()

        new_ants = dict(
            (ant.considered_position, ant)
            for ant in self.my_ants.values()
        )

        search_radius = self.attackradius2 * 9
        attack_radius = self.attackradius2
        offsets = ((-1, 0, 0), (0, -1, 0), (1, 0, 1), (2, 1, 0), (3, 0, -1)) 

        for apos, ant in new_ants.items():
            ant.enemy_checks += 1
            if ant.i_wont_move or ant.enemy_checks > 5:
                continue
            arow, acol = apos
            apos2 = ant.row, ant.col
            all_enemy_ants_nearby = enemy_cache.get(apos)
            if all_enemy_ants_nearby is None:
                all_enemy_ants_nearby = list(self.vector_ants(apos, self.enemy_ants.items(), search_radius, True))
                enemy_cache[apos] = all_enemy_ants_nearby
            if not all_enemy_ants_nearby:
                continue
            #err(len(all_enemy_ants_nearby), 'enemies nearby ant', apos)
            all_my_ants_nearby = list(self.vector_ants(apos, ((pos, 0) for pos in new_ants), search_radius, True))

            kills_enemy, kills_self = False, False
            kills_count = 0
            for enemy_direction, enemy_or, enemy_oc in offsets:
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
                #err(apos, ant.considered_direction, enemy_direction, enemy_or, enemy_oc, all_ants)
                my_enemies = list(self.vector_ants((0, 0), all_ants, attack_radius, True, 0))
                if not my_enemies:
                    continue
                min_enemy_weakness = min(
                    len(list(self.vector_ants(pos, all_ants, attack_radius, False, ant)))
                    for pos, ant in my_enemies
                )
                my_weakness = len(my_enemies)
                dont_go = False
                #err(my_weakness, 'possible enemies moving', enemy_direction, 'around ant', apos2, 'after moving to', apos, 'with minimal weakness', min_enemy_weakness)
                #if min_enemy_weakness == my_weakness:
                #    if enemy_direction == -1:
                #        ant.considered_hold = True
                #        break
                if min_enemy_weakness <= my_weakness:
                    #ant.considered_hold = False
                    dont_go = True

                if dont_go:
                    #err('I may be killed, not going', ant.considered_direction)
                    ant.considered_moves_dict[ant.considered_direction] -= 5
                    changes_made = True
                    break

        return changes_made

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

        # less explorers if much of map is visible
        manager_list = list(self.managers_attackers)
        manager_list.extend(self.managers_explorers)
        #expand = self.explorer_expand * (1-self.area_visible)
        #manager_list.extend(
        #    (x+expand, y)
        #    for x, y in self.managers_explorers
        #)
        #err(self.turn, expand)
        #manager_list = self.managers_explorers + self.managers_attackers
        if self.turn > 40 and self.my_hills and pos in self.my_hills and self.hill_guards.get(pos, 0) < 7:
            # 50% chance
            manager_list.append((sum(x for x, y in manager_list)/2, self.manager_defender))
            #manager_list += ((sum(x for x, y in manager_list), self.manager_defender),)

        s = float(sum(x for x, y in manager_list))
        c = random.random()
        i = 0
        for x, manager in manager_list:
            i += x/s
            if c <= i:
                break

        if manager == self.manager_defender:
            self.hill_guards[pos] = self.hill_guards.get(pos, 0) + 1
            ant.hill = pos

        ant.manager = manager

    def get_food_map(self, target, regen = False):
        food_map = self.food_maps.get(target)

        if food_map:
            if not (regen and food_map[1] != self.turn):
                #err('map to', target, 'is', self.turn-food_map[1], 'turns old')
                return food_map[0]
            dmap, _ = food_map
        else:
            if self.cached_dmaps:
                dmap = self.cached_dmaps.pop(0)
            else:
                dmap = cstuff.DirectionMap()

        dmap.clear()
        dmap.set_walls(self.water_map.strides, -2)
        dmap.fill((target,), self.mx2*2)
        self.food_maps[target] = dmap, self.turn
        return dmap

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
                #err('ant', pos, 'is too far away')
                continue

            if ant.target:
                current_distance = self.food_maps[ant.target][0].get_pos((ant.row, ant.col))
                if current_distance <= tmp_distance:
                    #err('ant', pos, 'is closer to its current target', ant.target, 'distance', current_distance, '<=', tmp_distance)
                    continue
            distance = tmp_distance
            possible_targeter = ant

        ant = possible_targeter
        if not ant:
            #err('No ant available')
            return

        if ant == original:
            #err('Same ant found as targetter')
            return

        if ant.target and ant.target != target:
            #err('switching ant target')
            del self.food_targeters[ant.target]

        if original:
            #err('switching targetter')
            del self.food_targeters[original.target]
            original.target = None

        ant.target = target
        self.food_targeters[target] = ant
        #err('ant', (ant.row, ant.col), 'goes to', target)
        #err('food map looks like this:')
        #food_map.debug_print()

    def vector_ants(self, apos, ants, limit2=None, normal_output=False, exclude=None):
        ra, ca = apos
        for pos, ant in ants:
            if ant == exclude:
                continue

            distance, ir, ic = cstuff.vector_ants_speedup(ra, ca, pos)

            if limit2 and distance > limit2:
                continue

            if normal_output:
                yield (ir, ic), ant
            else:
                yield ir, ic, distance, ant

