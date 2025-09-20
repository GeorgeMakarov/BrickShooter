from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Triangle, Line
from kivy.core.window import Window
from kivy.clock import Clock
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

Window.clearcolor = (0, 0, 0, 1)


class CellWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_rect = Rectangle(pos=self.pos, size=self.size)
        self.inner_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)
        self.draw_background((0.2, 0.2, 0.2, 1))
        self.arrow = None

    def update_rect(self, *args):
        self.border_rect.pos = self.pos
        self.border_rect.size = self.size
        border_width = 2
        self.inner_rect.pos = (self.x + border_width, self.y + border_width)
        self.inner_rect.size = (self.width - 2 * border_width, self.height - 2 * border_width)

    def draw_background(self, color_tuple):
        self.canvas.before.clear()
        with self.canvas.before:
            # For VOID cells, just draw a single black rectangle.
            if color_tuple == (0, 0, 0, 1):
                Color(*color_tuple)
                self.border_rect = Rectangle(pos=self.pos, size=self.size)
                self.inner_rect = Rectangle(pos=self.pos, size=(0, 0)) # Hide inner
            else:
                # For colored bricks, draw border and inner rectangle
                darker_color_tuple = (*[c * 0.5 for c in color_tuple[:3]], color_tuple[3])
                
                # Border
                Color(*darker_color_tuple)
                self.border_rect = Rectangle(pos=self.pos, size=self.size)
                
                # Inner color
                Color(*color_tuple)
                border_width = 2
                self.inner_rect = Rectangle(
                    pos=(self.x + border_width, self.y + border_width),
                    size=(self.width - 2 * border_width, self.height - 2 * border_width)
                )

    def draw_arrow(self, intention):
        """Draws a directional arrow based on the brick's intention."""
        self.clear_arrow()
        if intention in [CellIntention.STAND, CellIntention.VOID]:
            return

        with self.canvas:
            Color(1, 1, 1, 0.8) # White, slightly transparent arrow
            
            # Arrow points are calculated based on the widget's center and size
            cx, cy = self.center_x, self.center_y
            w, h = self.width, self.height
            
            # Define points for a triangle
            if intention == CellIntention.TO_UP:
                points = [cx, cy + h*0.3, cx - w*0.3, cy - h*0.2, cx + w*0.3, cy - h*0.2]
            elif intention == CellIntention.TO_DOWN:
                points = [cx, cy - h*0.3, cx - w*0.3, cy + h*0.2, cx + w*0.3, cy + h*0.2]
            elif intention == CellIntention.TO_LEFT:
                points = [cx - w*0.3, cy, cx + w*0.2, cy + h*0.3, cx + w*0.2, cy - h*0.3]
            elif intention == CellIntention.TO_RIGHT:
                points = [cx + w*0.3, cy, cx - w*0.2, cy + h*0.3, cx - w*0.2, cy - h*0.3]
            else:
                return # Should not happen

            self.arrow = Triangle(points=points)

    def clear_arrow(self):
        """Removes the arrow graphic."""
        if self.arrow:
            self.canvas.remove(self.arrow)
            self.arrow = None


class GameWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self._resolution_event = None

        # Game Logic Data
        self.field = [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
        self.cell_widgets = [[CellWidget() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]

        # Game Area
        game_area = BoxLayout(orientation='vertical', size_hint=(0.75, 1))
        self.game_grid = GridLayout(cols=FIELD_SIZE, rows=FIELD_SIZE)

        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                self.game_grid.add_widget(self.cell_widgets[r][c])

        game_area.add_widget(self.game_grid)
        self.add_widget(game_area)

        # UI Panel
        ui_panel = BoxLayout(orientation='vertical', size_hint=(0.25, 1), spacing=10, padding=10)

        score_label = Label(text="Score: 0", size_hint_y=None, height=40)
        level_label = Label(text="Level: 0", size_hint_y=None, height=40)

        new_game_button = Button(text="New Game", size_hint_y=None, height=50)
        undo_button = Button(text="Undo", size_hint_y=None, height=50)

        # Diagnostic Label
        self.diag_label = Label(
            text='Hover over grid...', 
            size_hint_y=None, 
            height=60,
            halign='left',
            valign='top'
        )
        self.diag_label.bind(size=self.diag_label.setter('text_size'))


        ui_panel.add_widget(score_label)
        ui_panel.add_widget(level_label)
        ui_panel.add_widget(new_game_button)
        ui_panel.add_widget(undo_button)
        ui_panel.add_widget(self.diag_label)
        ui_panel.add_widget(Widget()) # Spacer

        self.add_widget(ui_panel)
        
        Window.bind(mouse_pos=self.on_mouse_pos)
        
        # Bind touch event for launching bricks
        self.game_grid.bind(on_touch_down=self.on_grid_touch)
        self.game_grid.bind(pos=self.draw_grid_lines, size=self.draw_grid_lines)
        
        self.new_game()

    def get_coords_from_pos(self, x, y):
        """Converts window coordinates to grid cell indices."""
        # Convert window coordinates to grid-local coordinates
        local_x = x - self.game_grid.x
        local_y = y - self.game_grid.y

        # Convert local coordinates to grid cell indices
        c = int(local_x / (self.game_grid.width / FIELD_SIZE))
        r = (FIELD_SIZE - 1) - int(local_y / (self.game_grid.height / FIELD_SIZE)) # Y is flipped

        # Boundary check
        if not (0 <= c < FIELD_SIZE and 0 <= r < FIELD_SIZE):
            return None, None
        
        return r, c

    def draw_grid_lines(self, *args):
        """Draws the white grid lines, omitting corners and thickening boundaries."""
        self.game_grid.canvas.after.clear()
        with self.game_grid.canvas.after:
            Color(1, 1, 1, 1) # White lines
            
            grid_x, grid_y = self.game_grid.pos
            grid_w, grid_h = self.game_grid.size
            cell_w = grid_w / FIELD_SIZE
            cell_h = grid_h / FIELD_SIZE

            # --- Thick boundary lines ---
            # Top boundary (at r=3)
            y = grid_y + grid_h - PLAY_AREA_START*cell_h
            Line(points=[grid_x + PLAY_AREA_START*cell_w, y, grid_x + PLAY_AREA_END*cell_w, y], width=1.5)
            # Bottom boundary (at r=13)
            y = grid_y + grid_h - PLAY_AREA_END*cell_h
            Line(points=[grid_x + PLAY_AREA_START*cell_w, y, grid_x + PLAY_AREA_END*cell_w, y], width=1.5)
            # Left boundary (at c=3)
            x = grid_x + PLAY_AREA_START*cell_w
            Line(points=[x, grid_y + grid_h - PLAY_AREA_START*cell_h, x, grid_y + grid_h - PLAY_AREA_END*cell_h], width=1.5)
            # Right boundary (at c=13)
            x = grid_x + PLAY_AREA_END*cell_w
            Line(points=[x, grid_y + grid_h - PLAY_AREA_START*cell_h, x, grid_y + grid_h - PLAY_AREA_END*cell_h], width=1.5)

            # --- Thin inner lines ---
            # Vertical
            for c in range(PLAY_AREA_START + 1, PLAY_AREA_END):
                x = grid_x + c*cell_w
                Line(points=[x, grid_y + grid_h - PLAY_AREA_START*cell_h, x, grid_y + grid_h - PLAY_AREA_END*cell_h], width=1)
            # Horizontal
            for r in range(PLAY_AREA_START + 1, PLAY_AREA_END):
                y = grid_y + grid_h - r*cell_h
                Line(points=[grid_x + PLAY_AREA_START*cell_w, y, grid_x + PLAY_AREA_END*cell_w, y], width=1)

    def on_grid_touch(self, instance, touch):
        """Called when the grid is clicked."""
        if not self.game_grid.collide_point(*touch.pos):
            return

        r, c = self.get_coords_from_pos(*touch.pos)
        if r is None:
            return

        print(f"Grid touched at ({c}, {r})")
        self.shoot_brick(r, c)

    def shoot_brick(self, r, c):
        """
        Handles the logic of shooting a brick from a launch zone.
        A shot is only valid if the cell adjacent to the trigger, inside the
        play area, is VOID.
        """
        shot_fired = False
        # Left launcher (c=2, r=3..12) -> shoots RIGHT
        if c == (PLAY_AREA_START - 1) and (PLAY_AREA_START <= r < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'left')
        # Right launcher (c=13, r=3..12) -> shoots LEFT
        elif c == PLAY_AREA_END and (PLAY_AREA_START <= r < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'right')
        # Top launcher (r=2, c=3..12) -> shoots DOWN
        elif r == (PLAY_AREA_START - 1) and (PLAY_AREA_START <= c < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'top')
        # Bottom launcher (r=13, c=3..12) -> shoots UP
        elif r == PLAY_AREA_END and (PLAY_AREA_START <= c < PLAY_AREA_END):
            shot_fired = self._handle_shot(r, c, 'bottom')

        if shot_fired:
            print("Shot fired, starting resolution cycle...")
            self.start_resolution_cycle()

    def _handle_shot(self, r, c, launcher_id):
        """Helper function to process a shot from a specific launcher."""
        
        # 1. Define launcher-specific parameters
        if launcher_id == 'left':
            print(f"Left launcher trigger clicked at row {r}")
            target_r, target_c = r, PLAY_AREA_START
            direction = CellIntention.TO_RIGHT
            ammo_indices = [(r, i) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]
        elif launcher_id == 'right':
            print(f"Right launcher trigger clicked at row {r}")
            target_r, target_c = r, PLAY_AREA_END - 1
            direction = CellIntention.TO_LEFT
            ammo_indices = [(r, i) for i in range(PLAY_AREA_END, FIELD_SIZE)]
        elif launcher_id == 'top':
            print(f"Top launcher trigger clicked at col {c}")
            target_r, target_c = PLAY_AREA_START, c
            direction = CellIntention.TO_DOWN
            ammo_indices = [(i, c) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]
        elif launcher_id == 'bottom':
            print(f"Bottom launcher trigger clicked at col {c}")
            target_r, target_c = PLAY_AREA_END - 1, c
            direction = CellIntention.TO_UP
            ammo_indices = [(i, c) for i in range(PLAY_AREA_END, FIELD_SIZE)]
        else:
            return False

        # 2. Check if the target cell in the play area is VOID
        if self.field[target_r][target_c].intention != CellIntention.VOID:
            print("  - Shot blocked. Play area cell is not VOID.")
            return False

        # 3. Check if there's a valid path (at least one obstacle)
        if not self._is_obstacle_in_path(target_r, target_c, direction):
            print("  - Shot blocked. Path is completely clear.")
            return False

        # 4. Find the first available ammo and launch it
        for ammo_r, ammo_c in ammo_indices:
            brick = self.field[ammo_r][ammo_c]
            if brick.intention != CellIntention.VOID:
                print(f"  - Found ammo at ({ammo_c}, {ammo_r}). Intention: {brick.intention.name}")
                brick.intention = direction
                print(f"  - Changed intention to {brick.intention.name}")
                return True # Shot fired successfully

        return False # Should not be reached if logic is correct

    def _is_obstacle_in_path(self, r, c, direction):
        """
        Checks if there is at least one non-VOID brick in a given direction
        from a starting point (exclusive) to the edge of the play area.
        """
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

    def start_resolution_cycle(self):
        """Starts the timer that drives the resolution process."""
        if self._resolution_event:
            return # Cycle is already running
        self._resolution_event = Clock.schedule_interval(self.resolution_step, 0.1)

    def stop_resolution_cycle(self):
        """Stops the resolution timer."""
        if self._resolution_event:
            self._resolution_event.cancel()
            self._resolution_event = None
            print("Board stable, resolution cycle stopped.")

    def resolution_step(self, dt):
        """
        Represents one tick of the resolution cycle.
        It tries to resolve movement, then matches, until the board is stable.
        """
        # Per the design document, match resolution should happen *before* movement.
        matched = self.find_and_remove_groups()
        moved = self.movement_resolution_step()
        crossed = self.handle_board_crossers()
        
        self.draw_field()

        # If nothing happened in this step, the board is stable.
        if not moved and not matched and not crossed:
            self.stop_resolution_cycle()
            
            # --- STABILITY CHECK ---
            # Now that the board is visually stable, we process non-animated logic.
            # Board crossing is now handled above as part of the main cycle.
            
            # If nothing crossed, try refilling the launch zones.
            refilled = self.refill_launch_zones()
            if refilled:
                self.start_resolution_cycle()

    def refill_launch_zones(self):
        """
        Scans all 40 launch queues. If a queue has a void in it,
        it shifts bricks outwards to fill the void and creates a new
        brick at the outermost cell.
        Returns True if any bricks were created or moved.
        """
        was_changed = False

        # Define all 40 queues
        top_queues = [[(r, c) for r in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)] for c in range(PLAY_AREA_START, PLAY_AREA_END)]
        bottom_queues = [[(r, c) for r in range(PLAY_AREA_END, FIELD_SIZE)] for c in range(PLAY_AREA_START, PLAY_AREA_END)]
        left_queues = [[(r, c) for c in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)] for r in range(PLAY_AREA_START, PLAY_AREA_END)]
        right_queues = [[(r, c) for c in range(PLAY_AREA_END, FIELD_SIZE)] for r in range(PLAY_AREA_START, PLAY_AREA_END)]
        all_queues = top_queues + bottom_queues + left_queues + right_queues

        for queue in all_queues:
            if self._refill_queue(queue):
                was_changed = True
        
        if was_changed:
            self.draw_field()

        return was_changed

    def _refill_queue(self, queue_coords):
        """
        Refills a single launch queue if it has a void.
        queue_coords is a list of (r, c) tuples, from innermost to outermost.
        Returns True if the queue was modified.
        """
        for i, (r, c) in enumerate(queue_coords):
            if self.field[r][c].intention == CellIntention.VOID:
                # Shift bricks from further out to fill the void
                for j in range(i, len(queue_coords) - 1):
                    r_dest, c_dest = queue_coords[j]
                    r_src, c_src = queue_coords[j + 1]
                    self.field[r_dest][c_dest] = self.field[r_src][c_src]
                
                # Create a new brick at the outermost cell
                r_new, c_new = queue_coords[-1]
                self.field[r_new][c_new] = Brick(intention=CellIntention.STAND, color_index=random.randint(0, 8))
                
                return True # Queue was changed
        return False


    def handle_board_crossers(self):
        """
        Checks the perimeter of the play area for bricks that need to enter
        the opposite launch zone. Shifts the launch zone queue to make room.
        Returns True if any bricks were moved.
        """
        was_changed = False
        
        # Define crossing checks: (source_row/col, direction, dest_queue_fetcher)
        checks = [
            # Top boundary -> bricks go UP
            {'line': [(PLAY_AREA_START, c) for c in range(PLAY_AREA_START, PLAY_AREA_END)], 
             'direction': CellIntention.TO_UP,
             'dest_queue': lambda r, c: [(i, c) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]},
            # Bottom boundary -> bricks go DOWN
            {'line': [(PLAY_AREA_END - 1, c) for c in range(PLAY_AREA_START, PLAY_AREA_END)],
             'direction': CellIntention.TO_DOWN,
             'dest_queue': lambda r, c: [(i, c) for i in range(PLAY_AREA_END, FIELD_SIZE)]},
            # Left boundary -> bricks go LEFT
            {'line': [(r, PLAY_AREA_START) for r in range(PLAY_AREA_START, PLAY_AREA_END)],
             'direction': CellIntention.TO_LEFT,
             'dest_queue': lambda r, c: [(r, i) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)]},
            # Right boundary -> bricks go RIGHT
            {'line': [(r, PLAY_AREA_END - 1) for r in range(PLAY_AREA_START, PLAY_AREA_END)],
             'direction': CellIntention.TO_RIGHT,
             'dest_queue': lambda r, c: [(r, i) for i in range(PLAY_AREA_END, FIELD_SIZE)]},
        ]

        for check in checks:
            for r_src, c_src in check['line']:
                if self._handle_crossing_brick(r_src, c_src, check['direction'], check['dest_queue']):
                    was_changed = True

        if was_changed:
            self.draw_field()

        return was_changed

    def _handle_crossing_brick(self, r_src, c_src, direction, dest_queue_fetcher):
        """
        Handles a single potential crossing brick. If it crosses, it moves the
        destination queue and places the brick. Returns True if a brick crossed.
        """
        brick = self.field[r_src][c_src]
        if brick.intention != direction:
            return False

        print(f"Brick at ({c_src}, {r_src}) crossed boundary moving {direction.name}.")
        
        dest_queue = dest_queue_fetcher(r_src, c_src)

        # Shift the destination queue to make room
        for i in range(len(dest_queue) - 1, 0, -1):
            r_dest, c_dest = dest_queue[i]
            r_prev, c_prev = dest_queue[i - 1]
            self.field[r_dest][c_dest] = self.field[r_prev][c_prev]

        # Place the crossing brick at the innermost cell of the destination queue
        r_innermost, c_innermost = dest_queue[0]
        self.field[r_innermost][c_innermost] = brick
        brick.intention = CellIntention.STAND
        
        # Clear the source cell
        self.field[r_src][c_src] = Brick()
        
        return True

    def movement_resolution_step(self):
        """
        Performs one pass of movement for all bricks with directional intention.
        Returns True if any brick was moved, False otherwise.
        """
        moves = [] # List of ((from_r, from_c), (to_r, to_c))
        
        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                brick = self.field[r][c]
                if brick.intention.value in range(1, 5): # TO_LEFT, TO_RIGHT, TO_UP, TO_DOWN
                    vec = brick.intention_vector
                    tr, tc = r + vec[1], c + vec[0]

                    # Diagnostic print
                    print(f"Checking brick at ({c}, {r}) with intention {brick.intention.name}. Target: ({tc}, {tr})")

                    # Prevent bricks from moving directly from the play area to a launch zone.
                    # They must stop at the boundary and be processed by handle_board_crossers.
                    is_in_play_area = (PLAY_AREA_START <= r < PLAY_AREA_END and
                                       PLAY_AREA_START <= c < PLAY_AREA_END)
                    is_target_outside = not (PLAY_AREA_START <= tr < PLAY_AREA_END and
                                             PLAY_AREA_START <= tc < PLAY_AREA_END)

                    if is_in_play_area and is_target_outside:
                        continue

                    if 0 <= tr < FIELD_SIZE and 0 <= tc < FIELD_SIZE and self.field[tr][tc].intention == CellIntention.VOID:
                        moves.append(((r, c), (tr, tc)))
        
        # Diagnostic print
        if moves:
            print(f"Moves to be made this step: {moves}")

        if not moves:
            return False

        # We can directly apply the moves by swapping.
        for source, dest in moves:
            sr, sc = source
            dr, dc = dest
            # Swap the brick object with the VOID brick object
            self.field[dr][dc], self.field[sr][sc] = self.field[sr][sc], self.field[dr][dc]

        return True

    def find_and_remove_groups(self, min_group_size=3):
        """
        Finds and removes groups of same-colored bricks of size >= min_group_size.
        Returns True if any groups were removed, False otherwise.
        """
        was_changed = False
        visited = [[False for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]

        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                if visited[r][c]:
                    continue

                brick = self.field[r][c]
                if brick.intention == CellIntention.VOID:
                    continue

                color_index = brick.color_index
                if color_index is None:
                    continue
                
                group = self._find_group(r, c, color_index, visited)

                # Mark all bricks in the found group as visited
                for gr, gc in group:
                    visited[gr][gc] = True
                
                if len(group) >= min_group_size:
                    print(f"Found group of size {len(group)} at ({c}, {r}). Removing.")
                    for gr, gc in group:
                        self.field[gr][gc] = Brick() # Set to VOID
                    was_changed = True

        return was_changed

    def _find_group(self, start_r, start_c, color_index, visited):
        """
        Performs a BFS to find all connected bricks of the same color.
        Returns a list of (r, c) tuples for the group.
        """
        q = [(start_r, start_c)]
        group = []
        visited_in_search = set()
        visited_in_search.add((start_r, start_c))
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

    def on_mouse_pos(self, window, pos):
        """Called when the mouse is moved."""
        # Check if mouse is over the grid
        if not self.game_grid.collide_point(*pos):
            self.diag_label.text = ""
            return
        
        r, c = self.get_coords_from_pos(*pos)
        if r is None:
            return

        brick = self.field[r][c]
        color_name = 'N/A'
        if brick.color_index is not None:
            color_name = COLOR_NAMES[brick.color_index]

        diag_text = f"Coord: ({c}, {r})\nIntention: {brick.intention.name}\nColor: {color_name}"
        self.diag_label.text = diag_text

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

        self.draw_field()

    def draw_field(self):
        """Updates the visual grid to match the logical field."""
        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                brick = self.field[r][c]
                cell = self.cell_widgets[r][c]
                if brick.intention == CellIntention.VOID:
                    cell.draw_background((0, 0, 0, 1)) # Black for empty
                else:
                    cell.draw_background(BRICK_COLORS[brick.color_index])
                
                cell.draw_arrow(brick.intention)


class BrickShooterApp(App):
    def build(self):
        return GameWidget()

if __name__ == '__main__':
    BrickShooterApp().run()
