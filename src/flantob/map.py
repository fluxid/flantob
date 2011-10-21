#coding:utf8

CELL_UNKNOWN = 0
CELL_LAND = 1
CELL_WATER = 2

class Map:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.strides = [[CELL_UNKNOWN for j in range(cols)] for i in range(rows)]

    def set_water(self, row, col):
        self.strides[row][col] = CELL_WATER

    def can_enter(self, row, col):
        return self.strides[row][col] != CELL_WATER

