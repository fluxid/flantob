#!/usr/bin/env python3
#coding:utf8

from flantob.controller import Controller
import time

if __name__ == '__main__':
    import sys
    def err(*args):
        print(*args, file=sys.stderr)
    class timer:
        def __init__(self, arg):
            self.arg = arg

        def __enter__(self):
            self.time = time.time()

        def __exit__(self, type_, value, traceback):
            err(self.arg, '%.4f'%(time.time()-self.time))

    __builtins__.err = err
    __builtins__.timer = timer
    controller = Controller()
    controller.run()
