#coding:utf8

from collections import deque

class Map:
    def __init__(self, rows, cols):
        self.rows = rows
        self.cols = cols
        self.strides = [[False]*cols for i in range(rows)]

    def set(self, row, col, value=True):
        row%=self.rows
        col%=self.cols
        self.strides[row][col] = True

    def get(self, row, col):
        row%=self.rows
        col%=self.cols
        return self.strides[row][col]

    def or_with(self, other):
        assert self.rows == other.rows
        assert self.cols == other.cols
        self.strides = [
            [
                cell1 or cell2
                for cell1, cell2 in zip(row1, row2)
            ]
            for row1, row2 in zip(other.strides, self.strides)
        ]

    def or_with_offset(self, other, row, col):
        for row2 in range(other.rows):
            stride = self.strides[(row+row2)%self.rows]
            stride2 = other.strides[row2]
            for col2 in range(other.cols):
                if stride2[col2]:
                    stride[(col+col2)%self.cols] = True

    def __contains__(self, other):
        row, col = other
        return self.get(row, col)

class DirectionMap:
    def __init__(self, game, prefill, init, limit):
        self.game = game
        strides = self.strides = [list(stride) for stride in init]
        prefill = set((row, col) for row, col in prefill if strides[row][col] != -2)
        for row, col in prefill:
            strides[row][col] = 0
        self.queue = deque(prefill)
        self.limit = limit
        #self.queue = set((row, col) for row, col in prefill if strides[row][col] != -1)
        #for row, stride in enumerate(self.strides):
        #    err(''.join(('#' if cell == -1 else ('+' if (row, col) in self.queue else '.')) for col, cell in enumerate(stride)))
        #err()
        self.ready = False
        self.resume()

    def resume(self):
        if self.ready:
            return
        queue = self.queue
        strides = self.strides
        rows, cols = self.game.rows, self.game.cols
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

        #for stride in self.strides:
        #    err(' '.join('%2d'%cell for cell in stride))
        #err()

    def get_pos(self, pos):
        row, col = pos
        return self.strides[row][col]



