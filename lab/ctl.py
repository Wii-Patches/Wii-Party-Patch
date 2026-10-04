#!/usr/bin/env python3
"""ctl.py <command...>  -- send one command to labd.py and print the reply"""
import socket, sys
s = socket.create_connection(('127.0.0.1', 2478), timeout=300)
s.sendall((' '.join(sys.argv[1:]) + '\n').encode())
print(s.makefile().readline().strip())
