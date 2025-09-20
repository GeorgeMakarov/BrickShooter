from kivy.clock import Clock
from kivy.core.window import Window

from model import GameModel, FIELD_SIZE
from view import GameWidget

class GameController:
    def __init__(self, model: GameModel, view: GameWidget):
        self.model = model
        self.view = view
        self.is_resolving = False

        self.view.game_grid.bind(on_touch_down=self.on_grid_touch)

    def start(self):
        """
        Called at the beginning of the game. We schedule the initial draw
        to happen on the next frame, ensuring all widgets are sized correctly.
        """
        self.view.draw_field(self.model.field)

    def on_grid_touch(self, instance, touch):
        if self.is_resolving or self.view.is_animating:
            return # Ignore clicks during resolution

        if not self.view.game_grid.collide_point(*touch.pos):
            return

        r, c = self.get_coords_from_pos(*touch.pos)
        if r is None:
            return
        
        if self.model.shoot_brick(r, c):
            self.start_resolution_cycle()

    def get_coords_from_pos(self, x, y):
        local_x = x - self.view.game_grid.x
        local_y = y - self.view.game_grid.y

        c = int(local_x / (self.view.game_grid.width / FIELD_SIZE))
        r = (FIELD_SIZE - 1) - int(local_y / (self.view.game_grid.height / FIELD_SIZE))

        if not (0 <= c < FIELD_SIZE and 0 <= r < FIELD_SIZE):
            return None, None
        
        return r, c

    def start_resolution_cycle(self):
        if self.is_resolving:
            return
        self.is_resolving = True
        self.movement_step()

    def movement_step(self, dt=None):
        self.view.is_animating = True

        moved_coords = self.model.movement_resolution_step()
        crossed = self.model.handle_board_crossers()

        if moved_coords or crossed:
            self.view.animate_events([], moved_coords, self.movement_step)
        else:
            self.group_removal_step()

    def group_removal_step(self, dt=None):
        matched_coords = self.model.find_and_remove_groups()

        if matched_coords:
            self.view.animate_events(matched_coords, [], self.movement_step)
        else:
            self.on_cycle_stable()

    def on_cycle_stable(self):
        """Called when a resolution_step finds no possible moves."""
        refilled = self.model.refill_launch_zones()
        if refilled:
            self.view.draw_field(self.model.field)
            Clock.schedule_once(self.movement_step, 0.2) # Short delay before next auto-resolve
        else:
            self.is_resolving = False
            self.view.is_animating = False
