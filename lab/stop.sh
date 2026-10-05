#!/bin/bash
# stop the lab: the flow, the daemon and its Dolphin (only this project's)
for pat in "lab/flows.py" "flows.py derby" "flows.py menu" "labd.py" "Dolphin -b -u /Volumes/SSD/larsen/Documents/Git/Wii-Party-Patch"; do
  for p in $(ps -axo pid=,command= | grep -F -- "$pat" | grep -v grep | grep -v "stop.sh" | awk '{print $1}'); do
    [ "$p" != "$$" ] && kill "$p" 2>/dev/null
  done
done
