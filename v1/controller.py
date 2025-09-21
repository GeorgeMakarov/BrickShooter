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
        self.view.new_game_button.bind(on_press=self.start_new_game)
        self.view.undo_button.bind(on_press=self.undo_last_move)

    def start(self):
        """
        Called at the beginning of the game. We schedule the initial draw
        to happen on the next frame, ensuring all widgets are sized correctly.
        """
        self.view.draw_field(self.model.field)
        print("Initial board state:")
        print(self.model.get_field_intentions_map())

    def start_new_game(self, *args):
        """Resets the game to its initial state."""
        self.model.new_game()
        self.view.draw_field(self.model.field)
        self.view.update_score(self.model.score)
        self.is_resolving = False
        self.view.is_animating = False
        print("--- NEW GAME STARTED ---")

    def undo_last_move(self, *args):
        """Reverts the game to the previous state."""
        if self.is_resolving or self.view.is_animating:
            print("Cannot undo while animations are in progress.")
            return

        if self.model.revert_to_previous_state():
            self.view.draw_field(self.model.field)
            self.view.update_score(self.model.score)
            print("Undo successful.")
        else:
            print("Undo failed: No history available.")

    def on_grid_touch(self, instance, touch):
        if self.is_resolving or self.view.is_animating:
            return # Ignore clicks during resolution

        if not self.view.game_grid.collide_point(*touch.pos):
            return

        r, c = self.get_coords_from_pos(*touch.pos)
        if r is None:
            return
        
        print(f"User clicked on ({r}, {c})")
        self.model.save_state()
        if self.model.shoot_brick(r, c):
            print("Shot fired.")
            self.start_resolution_cycle()
            print("Board state after shot:")
            print(self.model.get_field_intentions_map())

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
        print("--- Starting resolution cycle ---")
        self.is_resolving = True
        self.movement_step()

    def movement_step(self, dt=None):
        self.view.is_animating = True

        moved_coords = self.model.movement_resolution_step()
        print(f"Movement step: {len(moved_coords)} bricks moved.")
        crossed = self.model.handle_board_crossers()
        if crossed:
            print("A brick crossed into a launch zone.")

        if moved_coords or crossed:
            self.view.animate_events([], moved_coords, self.movement_step)
        else:
            self.group_removal_step()

    def group_removal_step(self, dt=None):
        matched_coords, score_this_turn = self.model.find_and_remove_groups()

        if matched_coords:
            print(f"Group removal: {len(matched_coords)} bricks removed for {score_this_turn} points.")
            self.view.update_score(self.model.score)
            self.view.animate_events(matched_coords, [], self.movement_step)
        else:
            self.on_cycle_stable()

    def on_cycle_stable(self):
        """Called when a resolution_step finds no possible moves."""
        print("--- Resolution cycle stable ---")
        refilled = self.model.refill_launch_zones()
        if refilled:
            print("Launch zones refilled.")
            self.view.draw_field(self.model.field)
            Clock.schedule_once(self.movement_step, 0.2) # Short delay before next auto-resolve
        else:
            self.is_resolving = False
            self.view.is_animating = False
            print("Final board state for this cycle:")
            print(self.model.get_field_intentions_map())
            
            is_over, reason = self.model.is_game_over()
            if is_over:
                self.view.show_game_over(reason)
