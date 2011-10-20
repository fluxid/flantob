#coding:utf8

CELL_UNKNOWN = 0
CELL_LAND = 1
CELL_WATER = 2

class Map:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.strides = [[CELL_LAND for j in range(rows)] for i in range(cols)]

    def set_water(self, row, col):
        self.strides[row][col] = CELL_WATER

