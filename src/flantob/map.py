#coding:utf8

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

