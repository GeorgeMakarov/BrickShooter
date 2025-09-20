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

class CellStatus(Enum):
    VOID = 0
    TO_LEFT = 1
    TO_RIGHT = 2
    TO_UP = 3
    TO_DOWN = 4
    STAND = 5

class Brick:
    def __init__(self, status=CellStatus.VOID, color_index=None):
        self.status = status
        self.color_index = color_index

    @property
    def intention_vector(self):
        """Returns the movement intention as a [col, row] vector."""
        if self.status == CellStatus.TO_LEFT:
            return [-1, 0]
        if self.status == CellStatus.TO_RIGHT:
            return [1, 0]
        if self.status == CellStatus.TO_UP:
            return [0, -1]
        if self.status == CellStatus.TO_DOWN:
            return [0, 1]
        return [0, 0] # for STAND and VOID

Window.clearcolor = (0, 0, 0, 1)


class CellWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)
        self.draw_background((0.2, 0.2, 0.2, 1))
        self.arrow = None

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def draw_background(self, color_tuple):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*color_tuple)
            self.rect = Rectangle(pos=self.pos, size=self.size)

    def draw_arrow(self, status):
        """Draws a directional arrow based on the brick's status."""
        self.clear_arrow()
        if status in [CellStatus.STAND, CellStatus.VOID]:
            return

        with self.canvas:
            Color(1, 1, 1, 0.8) # White, slightly transparent arrow
            
            # Arrow points are calculated based on the widget's center and size
            cx, cy = self.center_x, self.center_y
            w, h = self.width, self.height
            
            # Define points for a triangle
            if status == CellStatus.TO_UP:
                points = [cx, cy + h*0.3, cx - w*0.3, cy - h*0.2, cx + w*0.3, cy - h*0.2]
            elif status == CellStatus.TO_DOWN:
                points = [cx, cy - h*0.3, cx - w*0.3, cy + h*0.2, cx + w*0.3, cy + h*0.2]
            elif status == CellStatus.TO_LEFT:
                points = [cx - w*0.3, cy, cx + w*0.2, cy + h*0.3, cx + w*0.2, cy - h*0.3]
            elif status == CellStatus.TO_RIGHT:
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
        self.field = [[Brick() for _ in range(16)] for _ in range(16)]
        self.cell_widgets = [[CellWidget() for _ in range(16)] for _ in range(16)]

        # Game Area
        game_area = BoxLayout(orientation='vertical', size_hint=(0.75, 1))
        self.game_grid = GridLayout(cols=16, rows=16)

        for r in range(16):
            for c in range(16):
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

    def draw_grid_lines(self, *args):
        """Draws the white grid lines, omitting corners and thickening boundaries."""
        self.game_grid.canvas.after.clear()
        with self.game_grid.canvas.after:
            Color(1, 1, 1, 1) # White lines
            
            grid_x, grid_y = self.game_grid.pos
            grid_w, grid_h = self.game_grid.size
            cell_w = grid_w / 16
            cell_h = grid_h / 16

            # --- Thick boundary lines ---
            # Top boundary (at r=3)
            y = grid_y + grid_h - 3*cell_h
            Line(points=[grid_x + 3*cell_w, y, grid_x + 13*cell_w, y], width=1.5)
            # Bottom boundary (at r=13)
            y = grid_y + grid_h - 13*cell_h
            Line(points=[grid_x + 3*cell_w, y, grid_x + 13*cell_w, y], width=1.5)
            # Left boundary (at c=3)
            x = grid_x + 3*cell_w
            Line(points=[x, grid_y + grid_h - 3*cell_h, x, grid_y + grid_h - 13*cell_h], width=1.5)
            # Right boundary (at c=13)
            x = grid_x + 13*cell_w
            Line(points=[x, grid_y + grid_h - 3*cell_h, x, grid_y + grid_h - 13*cell_h], width=1.5)

            # --- Thin inner lines ---
            # Vertical
            for c in range(4, 13):
                x = grid_x + c*cell_w
                Line(points=[x, grid_y + grid_h - 3*cell_h, x, grid_y + grid_h - 13*cell_h], width=1)
            # Horizontal
            for r in range(4, 13):
                y = grid_y + grid_h - r*cell_h
                Line(points=[grid_x + 3*cell_w, y, grid_x + 13*cell_w, y], width=1)

    def on_grid_touch(self, instance, touch):
        """Called when the grid is clicked."""
        if not self.game_grid.collide_point(*touch.pos):
            return

        # Convert window coordinates to grid-local coordinates
        local_x = touch.pos[0] - self.game_grid.x
        local_y = touch.pos[1] - self.game_grid.y

        # Convert local coordinates to grid cell indices
        c = int(local_x / (self.game_grid.width / 16))
        r = 15 - int(local_y / (self.game_grid.height / 16)) # Y is flipped

        # Boundary check
        if not (0 <= c < 16 and 0 <= r < 16):
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
        # Left launcher
        if c == 2 and (3 <= r < 13):
            print(f"Left launcher trigger clicked at row {r}")
            if self.field[r][3].status == CellStatus.VOID:
                if self._is_obstacle_in_path(r, 3, CellStatus.TO_RIGHT):
                    for i in range(2, -1, -1):
                        brick = self.field[r][i]
                        if brick.status != CellStatus.VOID:
                            print(f"  - Found ammo at ({i}, {r}). Status: {brick.status.name}")
                            brick.status = CellStatus.TO_RIGHT
                            print(f"  - Changed status to {brick.status.name}")
                            shot_fired = True
                            break
                else:
                    print("  - Shot blocked. Path is completely clear.")
            else:
                print("  - Shot blocked. Play area cell is not VOID.")
        
        # Right launcher
        elif c == 13 and (3 <= r < 13):
            print(f"Right launcher trigger clicked at row {r}")
            if self.field[r][12].status == CellStatus.VOID:
                if self._is_obstacle_in_path(r, 12, CellStatus.TO_LEFT):
                    for i in range(13, 16):
                        brick = self.field[r][i]
                        if brick.status != CellStatus.VOID:
                            print(f"  - Found ammo at ({i}, {r}). Status: {brick.status.name}")
                            brick.status = CellStatus.TO_LEFT
                            print(f"  - Changed status to {brick.status.name}")
                            shot_fired = True
                            break
                else:
                    print("  - Shot blocked. Path is completely clear.")
            else:
                print("  - Shot blocked. Play area cell is not VOID.")

        # Top launcher
        elif r == 2 and (3 <= c < 13):
            print(f"Top launcher trigger clicked at col {c}")
            if self.field[3][c].status == CellStatus.VOID:
                if self._is_obstacle_in_path(3, c, CellStatus.TO_DOWN):
                    for i in range(2, -1, -1):
                        brick = self.field[i][c]
                        if brick.status != CellStatus.VOID:
                            print(f"  - Found ammo at ({c}, {i}). Status: {brick.status.name}")
                            brick.status = CellStatus.TO_DOWN
                            print(f"  - Changed status to {brick.status.name}")
                            shot_fired = True
                            break
                else:
                    print("  - Shot blocked. Path is completely clear.")
            else:
                print("  - Shot blocked. Play area cell is not VOID.")

        # Bottom launcher
        elif r == 13 and (3 <= c < 13):
            print(f"Bottom launcher trigger clicked at col {c}")
            if self.field[12][c].status == CellStatus.VOID:
                if self._is_obstacle_in_path(12, c, CellStatus.TO_UP):
                    for i in range(13, 16):
                        brick = self.field[i][c]
                        if brick.status != CellStatus.VOID:
                            print(f"  - Found ammo at ({c}, {i}). Status: {brick.status.name}")
                            brick.status = CellStatus.TO_UP
                            print(f"  - Changed status to {brick.status.name}")
                            shot_fired = True
                            break
                else:
                    print("  - Shot blocked. Path is completely clear.")
            else:
                print("  - Shot blocked. Play area cell is not VOID.")

        if shot_fired:
            print("Shot fired, starting resolution cycle...")
            self.start_resolution_cycle()

    def _is_obstacle_in_path(self, r, c, direction):
        """
        Checks if there is at least one non-VOID brick in a given direction
        from a starting point (exclusive) to the edge of the play area.
        """
        if direction == CellStatus.TO_RIGHT:
            for i in range(c + 1, 13):
                if self.field[r][i].status != CellStatus.VOID:
                    return True
        elif direction == CellStatus.TO_LEFT:
            for i in range(c - 1, 2, -1):
                if self.field[r][i].status != CellStatus.VOID:
                    return True
        elif direction == CellStatus.TO_DOWN:
            for i in range(r + 1, 13):
                if self.field[i][c].status != CellStatus.VOID:
                    return True
        elif direction == CellStatus.TO_UP:
            for i in range(r - 1, 2, -1):
                if self.field[i][c].status != CellStatus.VOID:
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
        moved = self.movement_resolution_step()

        # Future calls to match resolution will go here.
        
        self.draw_field()

        # If nothing happened in this step, the board is stable.
        if not moved: # and not matched
            self.stop_resolution_cycle()
            
            # --- STABILITY CHECK ---
            # Now that the board is visually stable, we process non-animated logic.
            crossed = self.handle_board_crossers()
            
            if crossed:
                self.start_resolution_cycle()
                return
            
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
        # Top queues (rows 0, 1, 2 for cols 3-12)
        for c in range(3, 13):
            for r in range(2, -1, -1): # Scan inside-out: 2, 1, 0
                if self.field[r][c].status == CellStatus.VOID:
                    # Shift bricks from further out to fill the void
                    for r_shift in range(r, 0, -1): # r, r-1, ... 1
                        self.field[r_shift][c] = self.field[r_shift - 1][c]
                    self.field[0][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))
                    was_changed = True
                    break # Move to the next column once a void is filled
        
        # Bottom queues (rows 13, 14, 15 for cols 3-12)
        for c in range(3, 13):
            for r in range(13, 16): # Scan inside-out: 13, 14, 15
                if self.field[r][c].status == CellStatus.VOID:
                    for r_shift in range(r, 15): # r, r+1, ... 14
                        self.field[r_shift][c] = self.field[r_shift + 1][c]
                    self.field[15][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))
                    was_changed = True
                    break

        # Left queues (cols 0, 1, 2 for rows 3-12)
        for r in range(3, 13):
            for c in range(2, -1, -1): # Scan inside-out: 2, 1, 0
                if self.field[r][c].status == CellStatus.VOID:
                    for c_shift in range(c, 0, -1): # c, c-1, ... 1
                        self.field[r][c_shift] = self.field[r][c_shift - 1]
                    self.field[r][0] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))
                    was_changed = True
                    break

        # Right queues (cols 13, 14, 15 for rows 3-12)
        for r in range(3, 13):
            for c in range(13, 16): # Scan inside-out: 13, 14, 15
                if self.field[r][c].status == CellStatus.VOID:
                    for c_shift in range(c, 15): # c, c+1, ... 14
                        self.field[r][c_shift] = self.field[r][c_shift + 1]
                    self.field[r][15] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))
                    was_changed = True
                    break
        
        if was_changed:
            self.draw_field()

        return was_changed

    def handle_board_crossers(self):
        """
        Checks the perimeter of the play area for bricks that need to enter
        the opposite launch zone. Shifts the launch zone queue to make room.
        Returns True if any bricks were moved.
        """
        was_changed = False
        # Check top row of play area for bricks going UP
        for c in range(3, 13):
            brick = self.field[3][c]
            if brick.status == CellStatus.TO_UP:
                print(f"Brick at ({c}, 3) crossed top boundary.")
                # Shift the entire destination queue down
                for r_shift in range(0, 2): # r=0, 1
                    self.field[r_shift][c] = self.field[r_shift + 1][c]
                # Place the crossing brick at the innermost cell
                self.field[2][c] = brick
                brick.status = CellStatus.STAND
                # Clear the source cell
                self.field[3][c] = Brick()
                was_changed = True

        # Check bottom row of play area for bricks going DOWN
        for c in range(3, 13):
            brick = self.field[12][c]
            if brick.status == CellStatus.TO_DOWN:
                print(f"Brick at ({c}, 12) crossed bottom boundary.")
                for r_shift in range(15, 13, -1): # r=15, 14
                    self.field[r_shift][c] = self.field[r_shift - 1][c]
                self.field[13][c] = brick
                brick.status = CellStatus.STAND
                self.field[12][c] = Brick()
                was_changed = True

        # Check left col of play area for bricks going LEFT
        for r in range(3, 13):
            brick = self.field[r][3]
            if brick.status == CellStatus.TO_LEFT:
                print(f"Brick at (3, {r}) crossed left boundary.")
                for c_shift in range(0, 2): # c=0, 1
                    self.field[r][c_shift] = self.field[r][c_shift + 1]
                self.field[r][2] = brick
                brick.status = CellStatus.STAND
                self.field[r][3] = Brick()
                was_changed = True

        # Check right col of play area for bricks going RIGHT
        for r in range(3, 13):
            brick = self.field[r][12]
            if brick.status == CellStatus.TO_RIGHT:
                print(f"Brick at (12, {r}) crossed right boundary.")
                for c_shift in range(15, 13, -1): # c=15, 14
                    self.field[r][c_shift] = self.field[r][c_shift - 1]
                self.field[r][13] = brick
                brick.status = CellStatus.STAND
                self.field[r][12] = Brick()
                was_changed = True
        
        if was_changed:
            self.draw_field()

        return was_changed

    def movement_resolution_step(self):
        """
        Performs one pass of movement for all bricks with directional status.
        Returns True if any brick was moved, False otherwise.
        """
        moves = [] # List of ((from_r, from_c), (to_r, to_c))
        
        for r in range(16):
            for c in range(16):
                brick = self.field[r][c]
                if brick.status.value in range(1, 5): # TO_LEFT, TO_RIGHT, TO_UP, TO_DOWN
                    vec = brick.intention_vector
                    tr, tc = r + vec[1], c + vec[0]

                    # Diagnostic print
                    print(f"Checking brick at ({c}, {r}) with status {brick.status.name}. Target: ({tc}, {tr})")

                    if 0 <= tr < 16 and 0 <= tc < 16 and self.field[tr][tc].status == CellStatus.VOID:
                        moves.append(((r, c), (tr, tc)))
        
        # Diagnostic print
        if moves:
            print(f"Moves to be made this step: {moves}")

        if not moves:
            return False

        # For now, we assume no collisions (two bricks moving to the same cell).
        # We can directly apply the moves by swapping.
        for source, dest in moves:
            sr, sc = source
            dr, dc = dest
            # Swap the brick object with the VOID brick object
            self.field[dr][dc], self.field[sr][sc] = self.field[sr][sc], self.field[dr][dc]

        return True

    def on_mouse_pos(self, window, pos):
        """Called when the mouse is moved."""
        # Check if mouse is over the grid
        if not self.game_grid.collide_point(*pos):
            self.diag_label.text = ""
            return
        
        # Convert window coordinates to grid-local coordinates
        local_x = pos[0] - self.game_grid.x
        local_y = pos[1] - self.game_grid.y

        # Convert local coordinates to grid cell indices
        c = int(local_x / (self.game_grid.width / 16))
        r = 15 - int(local_y / (self.game_grid.height / 16)) # Y is flipped

        # Boundary check
        if not (0 <= c < 16 and 0 <= r < 16):
            return

        brick = self.field[r][c]
        color_name = 'N/A'
        if brick.color_index is not None:
            color_name = COLOR_NAMES[brick.color_index]

        diag_text = f"Coord: ({c}, {r})\nStatus: {brick.status.name}\nColor: {color_name}"
        self.diag_label.text = diag_text

    def new_game(self, level=0):
        """Initializes the game board for a new game."""
        self.field = [[Brick() for _ in range(16)] for _ in range(16)]

        # Top launch zone
        for c in range(3, 13):
            for r in range(3):
                self.field[r][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))
        
        # Bottom launch zone
        for c in range(3, 13):
            for r in range(13, 16):
                self.field[r][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))

        # Left launch zone
        for c in range(3):
            for r in range(3, 13):
                self.field[r][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))

        # Right launch zone
        for c in range(13, 16):
            for r in range(3, 13):
                self.field[r][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))

        # Add random obstacles to the play area
        num_obstacles = 2
        placed_obstacles = 0
        while placed_obstacles < num_obstacles:
            r, c = random.randint(3, 12), random.randint(3, 12)
            if self.field[r][c].status == CellStatus.VOID:
                self.field[r][c] = Brick(status=CellStatus.STAND, color_index=random.randint(0, 8))
                placed_obstacles += 1

        self.draw_field()

    def draw_field(self):
        """Updates the visual grid to match the logical field."""
        for r in range(16):
            for c in range(16):
                brick = self.field[r][c]
                cell = self.cell_widgets[r][c]
                if brick.status == CellStatus.VOID:
                    cell.draw_background((0, 0, 0, 1)) # Black for empty
                else:
                    cell.draw_background(BRICK_COLORS[brick.color_index])
                
                cell.draw_arrow(brick.status)


class BrickShooterApp(App):
    def build(self):
        return GameWidget()

if __name__ == '__main__':
    BrickShooterApp().run()
