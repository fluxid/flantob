#!/usr/bin/env python3
#coding:utf8

from flantob.controller import Controller

if __name__ == '__main__':
    import sys
    def err(*args):
        print(*args, file=sys.stderr)
    __builtins__.err = err
    controller = Controller()
    controller.run()
