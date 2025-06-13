import os
import msvcrt
import time
import sys
import threading
from collections import deque
import copy

fire_x = fire_y = water_x = water_y = 0
fire_score = water_score = 0
REQUIRED_FIRE = REQUIRED_WATER = 0
enemy1_x = enemy1_y = enemy2_x = enemy2_y = -1
at_positions = []
amp_positions = []
game_over_flag = False

STAGE_MAPS = [
    [
        list("#############################"),
        list("#w...............+..........#"),
        list("#f...............=..........#"),
        list("#####################.......#"),
        list("#.............=.............#"),
        list("#.............+.............#"),
        list("#.....#######################"),
        list("#.....=.....................#"),
        list("#.....+.....................#"),
        list("#############################")
    ],
    [
        list("#######################################"),
        list("#w..........&....+....................#"),
        list("#f..........&....=....................#"),
        list("#########@######...@..................#"),
        list("#######################.....+.........#"),
        list("#.....................................#"),
        list("#................................=....#"),
        list("#.......:::::::::::::##################"),
        list("#.....+...............................#"),
        list("#..........=..........................#"),
        list("###################################...#"),
        list("#...............=.....................#"),
        list("#...........................+.........#"),
        list("#######################################")
    ],
    [
        list("##################################################"),
        list("#w...............+..............................f#"),
        list("#################.....................:::........#"),
        list("###########################.......:::::::::::....#"),
        list("#######################......=....::.@......:....#"),
        list("######################............:::::::::.:....#"),
        list("#.........................................:.::...#"),
        list("#.......##################################:..:::=#"),
        list("#.....+...................................::....:#"),
        list("#.........................=...............::::.:.#"),
        list("#.........#########################......#...:..:#"),
        list("###########.....=........................###..:.:#"),
        list("#&&&&&&.....................+....................#"),
        list("#=....&......#####################################"),
        list("#..+..&..........................................#"),
        list("#.....&..........................................#"),
        list("#########################################........#"),
        list("#.....+.....+...................=................#"),
        list("#.....=.....=...................+................#"),
        list("##################################################")
    ]
]

STAGE_SETTINGS = [
    {"fire_start": (27, 7), "water_start": (27, 8), "enemy": False, "REQUIRED_FIRE": 3, "REQUIRED_WATER": 3},
    {"fire_start": (2, 11), "water_start": (2, 12), "enemy": False, "REQUIRED_FIRE": 4, "REQUIRED_WATER": 4},
    {"fire_start": (1, 18), "water_start": (1, 17), "enemy": True, "enemy1_start": (2, 1), "enemy2_start": (40, 1), "REQUIRED_FIRE": 7, "REQUIRED_WATER": 8}
]

def show_stage_intro(stage_idx):
    os.system('cls')
    print(f"\n   Stage {stage_idx + 1} 설명 ")
    print("- F(Fireboy)는 '+'를, W(Watergirl)는 '='를 먹어야 합니다.")
    print("- 각각 필요한 개수를 모두 모아야 클리어 조건이 됩니다.")
    print("- 마지막엔 F는 'f', W는 'w' 지점으로 이동해야 합니다.")

    if stage_idx == 1:
        print("- 함정(:)은 닿으면 즉사입니다.")
        print("- @ 스위치 위에 서 있을 때만 & 벽이 사라집니다")
    if stage_idx == 2:
        print("- 적(E)이 등장합니다 F 또는 W를 쫓아옵니다")
        print("- 적과 닿으면 즉시 게임 오버입니다.")
    print("\n[ENTER]를 누르면 시작합니다...")

    while True:
        if msvcrt.kbhit() and msvcrt.getch() == b'\r':
            break

def draw_map(map_data, WIDTH, HEIGHT):
    sys.stdout.write('\x1b[H')
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if (x, y) == (fire_x, fire_y):
                print('F', end='')
            elif (x, y) == (water_x, water_y):
                print('W', end='')
            elif (x, y) in [(enemy1_x, enemy1_y), (enemy2_x, enemy2_y)]:
                print('E', end='')
            else:
                print(map_data[y][x], end='')
        print()
    print(f"Fireboy 점수: {fire_score}/{REQUIRED_FIRE} | Watergirl 점수: {water_score}/{REQUIRED_WATER}")
    print("조작: Fireboy(WASD), Watergirl(IJKL), Q 종료")

def trigger_game_over(message, map_data, WIDTH, HEIGHT):
    global game_over_flag
    game_over_flag = True
    draw_map(map_data, WIDTH, HEIGHT)
    print(message)
    msvcrt.getch()
    sys.exit(0)

def check_clear(map_data):
    return (map_data[fire_y][fire_x] == 'f' and map_data[water_y][water_x] == 'w' and
            fire_score >= REQUIRED_FIRE and water_score >= REQUIRED_WATER)

def update_score(x, y, target, symbol, map_data):
    global fire_score, water_score
    if symbol == 'F' and target == '+':
        fire_score += 1
        map_data[y][x] = ' '
    elif symbol == 'W' and target == '=':
        water_score += 1
        map_data[y][x] = ' '

def move_player(x, y, dx, dy, symbol, map_data, WIDTH, HEIGHT):
    nx, ny = x + dx, y + dy
    if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
        target = map_data[ny][nx]
        amp_unlocked = any((fire_x, fire_y) == at or (water_x, water_y) == at for at in at_positions)
        if target == '#' or (target == '&' and not amp_unlocked):
            return x, y, ' '
        return nx, ny, target
    return x, y, ' '

def handle_move(x, y, dx, dy, symbol, map_data, WIDTH, HEIGHT):
    nx, ny, t = move_player(x, y, dx, dy, symbol, map_data, WIDTH, HEIGHT)
    if t == ':':
        trigger_game_over("\n 함정에 빠졌습니다 게임 오버", map_data, WIDTH, HEIGHT)
    update_score(nx, ny, t, symbol, map_data)
    return nx, ny

def find_next_step(start_x, start_y, goal_x, goal_y, map_data, WIDTH, HEIGHT):
    visited = [[False] * WIDTH for _ in range(HEIGHT)]
    prev = [[None] * WIDTH for _ in range(HEIGHT)]
    dq = deque([(start_x, start_y)])
    visited[start_y][start_x] = True

    while dq:
        x, y = dq.popleft()
        if (x, y) == (goal_x, goal_y):
            path = []
            while (x, y) != (start_x, start_y):
                path.append((x, y))
                x, y = prev[y][x]
            path.reverse()
            return path[0] if path else (start_x, start_y)
        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT and not visited[ny][nx] and map_data[ny][nx] != '#':
                visited[ny][nx] = True
                prev[ny][nx] = (x, y)
                dq.append((nx, ny))
    return start_x, start_y

def move_enemy(ex, ey, fx, fy, wx, wy, map_data, WIDTH, HEIGHT):
    df = abs(ex - fx) + abs(ey - fy)
    dw = abs(ex - wx) + abs(ey - wy)
    tx, ty = (fx, fy) if df <= dw else (wx, wy)
    return find_next_step(ex, ey, tx, ty, map_data, WIDTH, HEIGHT)

def play_stage(stage_idx):
    global fire_x, fire_y, water_x, water_y, fire_score, water_score
    global REQUIRED_FIRE, REQUIRED_WATER, enemy1_x, enemy1_y, enemy2_x, enemy2_y
    global at_positions, amp_positions, game_over_flag

    game_over_flag = False
    map_data = copy.deepcopy(STAGE_MAPS[stage_idx])
    HEIGHT, WIDTH = len(map_data), len(map_data[0])
    setting = STAGE_SETTINGS[stage_idx]

    fire_x, fire_y = setting['fire_start']
    water_x, water_y = setting['water_start']
    fire_score = water_score = 0
    REQUIRED_FIRE, REQUIRED_WATER = setting['REQUIRED_FIRE'], setting['REQUIRED_WATER']

    if setting.get("enemy"):
        enemy1_x, enemy1_y = setting["enemy1_start"]
        enemy2_x, enemy2_y = setting["enemy2_start"]

    at_positions.clear()
    amp_positions.clear()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if map_data[y][x] == '@':
                at_positions.append((x, y))
            elif map_data[y][x] == '&':
                amp_positions.append((x, y))

    def enemy_chase_loop():
        global enemy1_x, enemy1_y, enemy2_x, enemy2_y
        while not game_over_flag:
            time.sleep(2.0)
            enemy1_x, enemy1_y = move_enemy(enemy1_x, enemy1_y, fire_x, fire_y, water_x, water_y, map_data, WIDTH, HEIGHT)
            enemy2_x, enemy2_y = move_enemy(enemy2_x, enemy2_y, fire_x, fire_y, water_x, water_y, map_data, WIDTH, HEIGHT)
            if (fire_x, fire_y) in [(enemy1_x, enemy1_y), (enemy2_x, enemy2_y)] or \
               (water_x, water_y) in [(enemy1_x, enemy1_y), (enemy2_x, enemy2_y)]:
                trigger_game_over("\n 적에게 잡혔습니다 게임 오버", map_data, WIDTH, HEIGHT)

    if setting.get("enemy"):
        threading.Thread(target=enemy_chase_loop, daemon=True).start()

    os.system('cls')
    sys.stdout.write('\x1b[2J\x1b[H')

    while not game_over_flag:
        amp_unlocked = any((fire_x, fire_y) == at or (water_x, water_y) == at for at in at_positions)
        for x, y in amp_positions:
            map_data[y][x] = '.' if amp_unlocked else '&'

        draw_map(map_data, WIDTH, HEIGHT)

        if msvcrt.kbhit():
            key = msvcrt.getch().lower()
            if key == b'q':
                print("게임 종료")
                sys.exit(0)

            key_map = {
                b'w': (0, -1, 'F'), b's': (0, 1, 'F'), b'a': (-1, 0, 'F'), b'd': (1, 0, 'F'),
                b'i': (0, -1, 'W'), b'k': (0, 1, 'W'), b'j': (-1, 0, 'W'), b'l': (1, 0, 'W')
            }

            if key in key_map:
                dx, dy, symbol = key_map[key]
                if symbol == 'F':
                    fire_x, fire_y = handle_move(fire_x, fire_y, dx, dy, symbol, map_data, WIDTH, HEIGHT)
                else:
                    water_x, water_y = handle_move(water_x, water_y, dx, dy, symbol, map_data, WIDTH, HEIGHT)

            if not game_over_flag and check_clear(map_data):
                draw_map(map_data, WIDTH, HEIGHT)
                print("\n 스테이지 클리어")
                msvcrt.getch()
                return True
        time.sleep(0.05)
    return False

def main():
    for i in range(3):
        show_stage_intro(i)
        cleared = play_stage(i)
        if not cleared:
            print(f"\nStage {i + 1} 클리어 실패. 게임 종료.")
            return
    print("\n 모든 스테이지 클리어")

if __name__ == '__main__':
    main()
