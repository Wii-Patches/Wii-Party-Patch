#!/usr/bin/env python3
"""stop the lab: the flow, the daemon and its Dolphin (this project's only)"""
import os, signal, subprocess
me = {os.getpid(), os.getppid()}
for l in subprocess.run(['ps', '-axo', 'pid=,command='], capture_output=True, text=True).stdout.splitlines():
    pid, cmd = l.strip().split(None, 1)
    if int(pid) in me or 'stop.py' in cmd or cmd.startswith(('/bin/zsh', '/bin/bash')):
        continue
    if 'labd.py' in cmd or 'lab/flows.py' in cmd or 'flows.py' in cmd.split()[-2:] or \
       ('Dolphin -b -u /Volumes/SSD/larsen/Documents/Git/Wii-Party-Patch' in cmd):
        os.kill(int(pid), signal.SIGTERM)
        print('stopped', pid)
