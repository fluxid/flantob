#coding:utf8

from collections import deque
from copy import deepcopy

from . import cstuff

class Map:
    '''
    -1 empty
    -2 taken
    values to optimize DirectionMap initialization
    '''
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.strides = [[-1]*cols for i in range(rows)]

    def set(self, row, col, value=-2):
        row%=self.rows
        col%=self.cols
        self.strides[row][col] = value

    def get(self, row, col=None):
        if col is None:
            row, col = row
        row%=self.rows
        col%=self.cols
        return self.strides[row][col] == -2

    def or_with(self, other):
        self.strides = [
            [
                (-2 if (cell1 == -2 or cell2 == -2) else -1)
                for cell1, cell2 in zip(row1, row2)
            ]
            for row1, row2 in zip(other.strides, self.strides)
        ]

    def or_with_offset(self, other, row, col):
        for row2 in range(other.rows):
            stride = self.strides[(row+row2)%self.rows]
            stride2 = other.strides[row2]
            for col2 in range(other.cols):
                if stride2[col2] == -2:
                    stride[(col+col2)%self.cols] = -2

    def __contains__(self, other):
        row, col = other
        return self.get(row, col)

    def direction_map_init(self):
        return [list(stride) for stride in self.strides]

    def direction_map_edge_prefill(self):
        return direction_map_edge_prefill(self.strides, self.rows, self.cols)

    def debug_print(self):
        for stride in self.strides:
            err(' '.join(('#' if (cell == -2) else '.') for cell in stride))

def direction_map_edge_prefill(strides, rows, cols):
    last_stride = strides[-1]
    for row, stride in enumerate(strides):
        last_cell = stride[-1] == -2
        for col, cell in enumerate(stride):
            cell = cell == -2
            if cell and not last_cell:
                yield (row, col)
            elif not cell and last_cell:
                yield (row, (col-1)%cols)
            else:
                last_cell = last_stride[col] == -2
                if cell and not last_cell:
                    yield (row, col)
                elif not cell and last_cell:
                    yield ((row-1)%rows, col)
            last_cell = cell
        last_stride = stride

