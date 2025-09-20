from enum import Enum
import random

BRICK_COLORS = [
    (1, 0, 0, 1),       # 0: red
    (0, 1, 0, 1),       # 1: green
    (0, 0, 1, 1),       # 2: blue
    (1, 1, 0, 1),       # 3: yellow
    (0.6, 0.25, 0, 1),  # 4: brown
    (0.3, 0.3, 0.3, 1), # 5: black/dark grey
    (0, 1, 1, 1),       # 6: cyan
    (1, 0, 1, 1),       # 7: magenta
    (1, 0.4, 0.7, 1),   # 8: rose
]

COLOR_NAMES = [
    'red', 'green', 'blue', 'yellow', 'brown', 
    'black', 'cyan', 'magenta', 'rose'
]

# --- Game Constants ---
FIELD_SIZE = 16
LAUNCH_ZONE_DEPTH = 3
PLAY_AREA_START = LAUNCH_ZONE_DEPTH
PLAY_AREA_END = FIELD_SIZE - LAUNCH_ZONE_DEPTH

class CellIntention(Enum):
    VOID = 0
    TO_LEFT = 1
    TO_RIGHT = 2
    TO_UP = 3
    TO_DOWN = 4
    STAND = 5

class Brick:
    def __init__(self, intention=CellIntention.VOID, color_index=None):
        self.intention = intention
        self.color_index = color_index

    @property
    def intention_vector(self):
        """Returns the movement intention as a [col, row] vector."""
        if self.intention == CellIntention.TO_LEFT:
            return [-1, 0]
        if self.intention == CellIntention.TO_RIGHT:
            return [1, 0]
        if self.intention == CellIntention.TO_UP:
            return [0, -1]
        if self.intention == CellIntention.TO_DOWN:
            return [0, 1]
        return [0, 0] # for STAND and VOID

class GameModel:
    def __init__(self):
        self.field = [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
        self.new_game()

    def new_game(self, level=0):
        """Initializes the game board for a new game."""
        self.field = [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]

        # Define launch zones and fill them
        zones = [
            {'rows': range(LAUNCH_ZONE_DEPTH), 'cols': range(PLAY_AREA_START, PLAY_AREA_END)},      # Top
            {'rows': range(PLAY_AREA_END, FIELD_SIZE), 'cols': range(PLAY_AREA_START, PLAY_AREA_END)}, # Bottom
            {'rows': range(PLAY_AREA_START, PLAY_AREA_END), 'cols': range(LAUNCH_ZONE_DEPTH)},      # Left
            {'rows': range(PLAY_AREA_START, PLAY_AREA_END), 'cols': range(PLAY_AREA_END, FIELD_SIZE)}  # Right
        ]
        for zone in zones:
            for r in zone['rows']:
                for c in zone['cols']:
                    self.field[r][c] = Brick(intention=CellIntention.STAND, color_index=random.randint(0, 8))

        # Add random obstacles to the play area
        num_obstacles = 2
        placed_obstacles = 0
        while placed_obstacles < num_obstacles:
            r, c = random.randint(PLAY_AREA_START, PLAY_AREA_END - 1), random.randint(PLAY_AREA_START, PLAY_AREA_END - 1)
            if self.field[r][c].intention == CellIntention.VOID:
                self.field[r][c] = Brick(intention=CellIntention.STAND, color_index=random.randint(0, 8))
                placed_obstacles += 1

    def movement_resolution_step(self):
        """
        Performs one pass of movement for all bricks with directional intention.
        Returns a list of moves that occurred.
        """
        moves = [] # List of ((from_r, from_c), (to_r, to_c))
        
        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                brick = self.field[r][c]
                if brick.intention.value in range(1, 5): # TO_LEFT, TO_RIGHT, TO_UP, TO_DOWN
                    vec = brick.intention_vector
                    tr, tc = r + vec[1], c + vec[0]

                    is_in_play_area = (PLAY_AREA_START <= r < PLAY_AREA_END and
                                       PLAY_AREA_START <= c < PLAY_AREA_END)
                    is_target_outside = not (PLAY_AREA_START <= tr < PLAY_AREA_END and
                                             PLAY_AREA_START <= tc < PLAY_AREA_END)

                    if is_in_play_area and is_target_outside:
                        continue

                    if 0 <= tr < FIELD_SIZE and 0 <= tc < FIELD_SIZE and self.field[tr][tc].intention == CellIntention.VOID:
                        moves.append(((r, c), (tr, tc)))
        
        if not moves:
            return []

        final_moves_map = {}
        for source, dest in moves:
            if dest not in final_moves_map:
                final_moves_map[dest] = source

        if not final_moves_map:
            return []

        for dest, source in final_moves_map.items():
            sr, sc = source
            dr, dc = dest
            self.field[dr][dc], self.field[sr][sc] = self.field[sr][sc], self.field[dr][dc]

        return [(source, dest) for dest, source in final_moves_map.items()]

    def find_and_remove_groups(self, min_group_size=3):
        """
        Finds and removes groups of same-colored bricks.
        Returns a list of coordinates of the removed bricks.
        """
        removed_bricks = []
        visited = [[False for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]

        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                if visited[r][c]:
                    continue

                brick = self.field[r][c]
                if brick.intention == CellIntention.VOID or brick.color_index is None:
                    continue
                
                group = self._find_group(r, c, brick.color_index, visited)

                for gr, gc in group:
                    visited[gr][gc] = True
                
                if len(group) >= min_group_size:
                    removed_bricks.extend(group)
                    for gr, gc in group:
                        self.field[gr][gc] = Brick()

        return removed_bricks

    def _find_group(self, start_r, start_c, color_index, visited):
        q = [(start_r, start_c)]
        group = []
        visited_in_search = set([(start_r, start_c)])
        visited[start_r][start_c] = True

        while q:
            r, c = q.pop(0)
            group.append((r, c))

            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc

                if not (PLAY_AREA_START <= nr < PLAY_AREA_END and PLAY_AREA_START <= nc < PLAY_AREA_END):
                    continue
                
                if (nr, nc) in visited_in_search:
                    continue

                neighbor_brick = self.field[nr][nc]
                if not visited[nr][nc] and neighbor_brick.intention != CellIntention.VOID and neighbor_brick.color_index == color_index:
                    visited_in_search.add((nr, nc))
                    visited[nr][nc] = True
                    q.append((nr, nc))

        return group

    def handle_board_crossers(self):
        was_changed = False
        
        checks = [
            {'line': [(PLAY_AREA_START, c) for c in range(PLAY_AREA_START, PLAY_AREA_END)], 
             'direction': CellIntention.TO_UP,
             'dest_queue': lambda r, c: [(i, c) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]},
            {'line': [(PLAY_AREA_END - 1, c) for c in range(PLAY_AREA_START, PLAY_AREA_END)],
             'direction': CellIntention.TO_DOWN,
             'dest_queue': lambda r, c: [(i, c) for i in range(PLAY_AREA_END, FIELD_SIZE)]},
            {'line': [(r, PLAY_AREA_START) for r in range(PLAY_AREA_START, PLAY_AREA_END)],
             'direction': CellIntention.TO_LEFT,
             'dest_queue': lambda r, c: [(r, i) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]},
            {'line': [(r, PLAY_AREA_END - 1) for r in range(PLAY_AREA_START, PLAY_AREA_END)],
             'direction': CellIntention.TO_RIGHT,
             'dest_queue': lambda r, c: [(r, i) for i in range(PLAY_AREA_END, FIELD_SIZE)]},
        ]

        for check in checks:
            for r_src, c_src in check['line']:
                if self._handle_crossing_brick(r_src, c_src, check['direction'], check['dest_queue']):
                    was_changed = True

        return was_changed

    def _handle_crossing_brick(self, r_src, c_src, direction, dest_queue_fetcher):
        brick = self.field[r_src][c_src]
        if brick.intention != direction:
            return False
        
        dest_queue = dest_queue_fetcher(r_src, c_src)

        for i in range(len(dest_queue) - 1, 0, -1):
            r_dest, c_dest = dest_queue[i]
            r_prev, c_prev = dest_queue[i - 1]
            self.field[r_dest][c_dest] = self.field[r_prev][c_prev]

        r_innermost, c_innermost = dest_queue[0]
        self.field[r_innermost][c_innermost] = brick
        brick.intention = CellIntention.STAND
        
        self.field[r_src][c_src] = Brick()
        
        return True

    def refill_launch_zones(self):
        was_changed = False
        top_queues = [[(r, c) for r in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)] for c in range(PLAY_AREA_START, PLAY_AREA_END)]
        bottom_queues = [[(r, c) for r in range(PLAY_AREA_END, FIELD_SIZE)] for c in range(PLAY_AREA_START, PLAY_AREA_END)]
        left_queues = [[(r, c) for c in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)] for r in range(PLAY_AREA_START, PLAY_AREA_END)]
        right_queues = [[(r, c) for c in range(PLAY_AREA_END, FIELD_SIZE)] for r in range(PLAY_AREA_START, PLAY_AREA_END)]
        all_queues = top_queues + bottom_queues + left_queues + right_queues

        for queue in all_queues:
            if self._refill_queue(queue):
                was_changed = True
        
        return was_changed

    def _refill_queue(self, queue_coords):
        for i, (r, c) in enumerate(queue_coords):
            if self.field[r][c].intention == CellIntention.VOID:
                for j in range(i, len(queue_coords) - 1):
                    r_dest, c_dest = queue_coords[j]
                    r_src, c_src = queue_coords[j + 1]
                    self.field[r_dest][c_dest] = self.field[r_src][c_src]
                
                r_new, c_new = queue_coords[-1]
                self.field[r_new][c_new] = Brick(intention=CellIntention.STAND, color_index=random.randint(0, 8))
                
                return True
        return False

    def shoot_brick(self, r, c):
        shot_fired = False
        if c == (PLAY_AREA_START - 1) and (PLAY_AREA_START <= r < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'left')
        elif c == PLAY_AREA_END and (PLAY_AREA_START <= r < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'right')
        elif r == (PLAY_AREA_START - 1) and (PLAY_AREA_START <= c < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'top')
        elif r == PLAY_AREA_END and (PLAY_AREA_START <= c < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'bottom')
        
        return shot_fired

    def _handle_shot(self, r, c, launcher_id):
        if launcher_id == 'left':
            target_r, target_c = r, PLAY_AREA_START
            direction = CellIntention.TO_RIGHT
            ammo_indices = [(r, i) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]
        elif launcher_id == 'right':
            target_r, target_c = r, PLAY_AREA_END - 1
            direction = CellIntention.TO_LEFT
            ammo_indices = [(r, i) for i in range(PLAY_AREA_END, FIELD_SIZE)]
        elif launcher_id == 'top':
            target_r, target_c = PLAY_AREA_START, c
            direction = CellIntention.TO_DOWN
            ammo_indices = [(i, c) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]
        elif launcher_id == 'bottom':
            target_r, target_c = PLAY_AREA_END - 1, c
            direction = CellIntention.TO_UP
            ammo_indices = [(i, c) for i in range(PLAY_AREA_END, FIELD_SIZE)]
        else:
            return False

        if self.field[target_r][target_c].intention != CellIntention.VOID:
            return False

        if not self._is_obstacle_in_path(target_r, target_c, direction):
            return False

        for ammo_r, ammo_c in ammo_indices:
            brick = self.field[ammo_r][ammo_c]
            if brick.intention != CellIntention.VOID:
                brick.intention = direction
                return True

        return False

    def _is_obstacle_in_path(self, r, c, direction):
        if direction == CellIntention.TO_RIGHT:
            for i in range(c + 1, PLAY_AREA_END):
                if self.field[r][i].intention != CellIntention.VOID:
                    return True
        if direction == CellIntention.TO_LEFT:
            for i in range(c - 1, PLAY_AREA_START - 1, -1):
                if self.field[r][i].intention != CellIntention.VOID:
                    return True
        if direction == CellIntention.TO_DOWN:
            for i in range(r + 1, PLAY_AREA_END):
                if self.field[i][c].intention != CellIntention.VOID:
                    return True
        if direction == CellIntention.TO_UP:
            for i in range(r - 1, PLAY_AREA_START - 1, -1):
                if self.field[i][c].intention != CellIntention.VOID:
                    return True
        return False
