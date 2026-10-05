"""Scripted flows against a running labd.py:  python3 flows.py <flow> [args]"""
import json, socket, sys, time


def cmd(*a):
    s = socket.create_connection(('127.0.0.1', 2478), timeout=300)
    s.sendall((' '.join(str(x) for x in a) + '\n').encode())
    r = s.makefile().readline().strip()
    s.close()
    try:
        return json.loads(r)
    except Exception:
        return r


def tap(*names, hold=0.3, gap=1.0, chan=0):
    return cmd('tap', chan, *names, 'hold=%s' % hold, 'gap=%s' % gap)


def to_title():
    cmd('pad', 0)
    time.sleep(40)
    for _ in range(3):
        tap('A', gap=4)


def skip_intro():
    """title -> the hosted intro -> the first menu (A mashed through the host's talk)"""
    tap('A', 'B', hold=0.6, gap=8)
    for _ in range(20):
        tap('A', gap=2.5)


def to_main_menu():
    to_title()
    tap('A', 'B', hold=0.8, gap=10)
    for _ in range(16):
        tap('A', gap=2.5)
    for _ in range(7):
        tap('B', gap=3)


def to_derby(players=1):
    """main menu -> Minigames -> Free Play -> n players -> the first minigame's rules page"""
    tap('D', gap=1.5); tap('D', gap=1.5); tap('RT', gap=1.5); tap('RT', gap=1.5)
    tap('A', gap=5)
    for _ in range(4):
        tap('A', gap=4)
    for c in (1, 2, 3):
        cmd('pad', c)
    time.sleep(5)
    for _ in range(players - 1):
        tap('RT', gap=1.5)
    tap('A', gap=6)
    for _ in range(3):
        tap('A', gap=4)
    for _ in range(2):
        tap('A', gap=6)
    for _ in range(3):
        tap('A', gap=5)
    time.sleep(25)


if __name__ == '__main__':
    f = sys.argv[1]
    if f == 'intro':
        to_title(); skip_intro()
    elif f == 'menu':
        to_main_menu()
    elif f == 'derby':
        to_main_menu(); to_derby()
    elif f == 'shot':
        print(cmd('shot', sys.argv[2]))
