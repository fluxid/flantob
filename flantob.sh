#!/bin/sh

WORKING_DIR="$(cd "${0%/*}" 2>/dev/null; dirname "$PWD"/"${0##*/}")"
cd ${WORKING_DIR}

#( time valgrind --log-fd=2 python3 ./src/MyBot.py3 ) 2> ./log.txt
#export MUDFLAP_OPTIONS='-print-leaks'
#tee bot.input | ( time python3 ./src/MyBot.py3 ) 2> ./log.txt
( time python3 ./src/MyBot.py3 "$@" ) 2> ./log.txt
#( time python3 -mcProfile -o ./lol.profile ./src/MyBot.py3 ) 2> ./log.txt
