#!/bin/bash -e

# if command starts with an option, prepend the default command and options
if [ "${1:0:1}" = '-' ]; then
  set -- aetherterm/server.py --unsecure --host=0.0.0.0 --port=${PORT:-57575} "$@"
elif [ "$1" = 'aetherterm/server.py' ]; then
  shift
  set -- aetherterm/server.py --unsecure --host=0.0.0.0 --port=${PORT:-57575} "$@"
fi

# Set password
echo "root:${PASSWORD:-password}" | chpasswd

exec "$@"
