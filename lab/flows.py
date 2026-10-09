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


def sig(path):
    from PIL import Image
    return list(Image.open(path).convert('L').resize((32, 18)).getdata())


def is_screen(name, tol=14.0):
    """does the game currently show the screen saved as refs/<name>.png?"""
    import os
    shot = cmd('shot', '/tmp/wp_cur.png')
    if shot == 'noframe':
        return False
    a, b = sig('/tmp/wp_cur.png'), sig(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'refs', name + '.png'))
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a) < tol


def until(name, *names, tries=40, gap=2.0, hold=0.3):
    """press `names` until the screen `name` shows up"""
    for _ in range(tries):
        if is_screen(name):
            return True
        tap(*names, hold=hold, gap=gap)
    raise RuntimeError('never reached ' + name)


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
    cmd('pad', 0)
    time.sleep(35)
    until('title', 'A', gap=3)
    tap('A', 'B', hold=0.8, gap=10)
    until('mainmenu', 'A', gap=2.5, tries=60)


def to_derby():
    """main menu -> Minigames -> Free Play -> 1 player -> Derby Dash's rules page (every step waits for its screen)"""
    for n in ('D', 'D', 'RT', 'RT'):
        tap(n, hold=0.5, gap=2)
    until('players', 'A', gap=7, hold=0.5, tries=20)
    for c in (1, 2, 3):
        cmd('pad', c)
    time.sleep(6)
    until('derby_rules', 'A', gap=8, hold=0.5, tries=40)


def to_derby_race():
    to_main_menu()
    to_derby()
    tap('A', hold=0.5, gap=35)


if __name__ == '__main__':
    f = sys.argv[1]
    if f == 'intro':
        to_title(); skip_intro()
    elif f == 'menu':
        to_main_menu()
    elif f == 'derby':
        to_main_menu(); to_derby()
    elif f == 'race':
        to_derby_race()
    elif f == 'shot':
        print(cmd('shot', sys.argv[2]))
