#coding:utf8

from collections import deque
from copy import deepcopy

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
        strides = self.strides
        last_stride = strides[-1]
        for row, stride in enumerate(strides):
            last_cell = stride[-1] == -2
            for col, cell in enumerate(stride):
                cell = cell == -2
                if cell and not last_cell:
                    yield (row, col)
                elif not cell and last_cell:
                    yield (row, col-1)
                else:
                    last_cell = last_stride[col] == -2
                    if cell and not last_cell:
                        yield (row, col)
                    elif not cell and last_cell:
                        yield (row-1, col)
                last_cell = cell
            last_stride = stride

    def debug_print(self):
        for stride in self.strides:
            err(' '.join(('#' if (cell == -2) else '.') for cell in stride))

class DirectionMap:
    def __init__(self, prefill, init, limit):
        strides = self.strides = init
        self.rows, self.cols = len(strides), len(strides[0])
        prefill = set((row, col) for row, col in prefill if strides[row][col] != -2)
        for row, col in prefill:
            strides[row][col] = 0
        self.queue = deque(prefill)
        self.limit = limit
        self.ready = False
        self.resume()

    def resume(self):
        if self.ready:
            return
        queue = self.queue
        strides = self.strides
        rows, cols = self.rows, self.cols
        while queue: #and podlicz czas:
            row, col = queue.popleft()
            stride = strides[row]
            value = stride[col] + 1
            if self.limit and value > self.limit:
                continue

            col2 = (col-1)%cols
            if stride[col2] == -1:
                self.queue.append((row, col2))
                stride[col2] = value

            col2 = (col+1)%cols
            if stride[col2] == -1:
                self.queue.append((row, col2))
                stride[col2] = value

            row2 = (row-1)%rows
            stride = strides[row2]
            if stride[col] == -1:
                self.queue.append((row2, col))
                stride[col] = value

            row2 = (row+1)%rows
            stride = strides[row2]
            if stride[col] == -1:
                self.queue.append((row2, col))
                stride[col] = value

        if not queue:
            self.ready=True

    def debug_print(self):
        for stride in self.strides:
            err(' '.join(('##' if cell == -2 else '__' if cell == -1 else '%2d'%cell) for cell in stride))
        err()

    def get_pos(self, pos):
        row, col = pos
        return self.strides[row][col]

    def invert(self):
        self.strides = [
            [
                (self.limit - cell if cell >= 0 else cell)
                for cell in stride
            ]
            for stride in self.strides
        ]

