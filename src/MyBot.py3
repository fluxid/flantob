#!/usr/bin/env python3
#coding:utf8

from flantob.controller import Controller
import time

if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if args:
        filename = args.pop()
    else:
        filename = None

    def err(*args):
        print(*args, file=sys.stderr)
        sys.stderr.flush()
    class timer:
        def __init__(self, arg):
            self.arg = arg

        def __enter__(self):
            self.time = time.time()

        def __exit__(self, type_, value, traceback):
            err(self.arg, '%dms'%((time.time()-self.time)*1000))

    if isinstance(__builtins__, dict):
        __builtins__['err'] = err
        __builtins__['timer'] = timer
    else:
        __builtins__.err = err
        __builtins__.timer = timer
    controller = Controller(filename)
    controller.run()
