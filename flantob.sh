#!/bin/sh

WORKING_DIR="$(cd "${0%/*}" 2>/dev/null; dirname "$PWD"/"${0##*/}")"
cd ${WORKING_DIR}

( time python3 ./src/MyBot.py3 ) 2> ./log.txt
#( time python3 -mcProfile -o ./lol.profile ./src/MyBot.py3 ) 2> ./log.txt
