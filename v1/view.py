from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.checkbox import CheckBox
from kivy.graphics import Color, Rectangle, Triangle, Line
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.graphics.instructions import InstructionGroup
from kivy.app import App
import copy

from model import FIELD_SIZE, PLAY_AREA_START, PLAY_AREA_END, CellIntention, Brick

import os

BRICK_SKIN_PATH = os.path.join(os.path.dirname(__file__), 'assets', 'NBricks.bmp')
N_BRICK_COLORS = 10

def _get_texture_coords(brick):
    """Calculates texture coordinates for a given brick."""
    if brick.intention == CellIntention.VOID:
        return 0, 0, 0, 0

    intention = brick.intention
    u0, u1 = 0, 0.2
    if intention == CellIntention.TO_RIGHT:
        u0, u1 = 0.2, 0.4
    elif intention == CellIntention.TO_UP:
        u0, u1 = 0.8, 1.0
    elif intention == CellIntention.TO_LEFT:
        u0, u1 = 0.6, 0.8
    elif intention == CellIntention.TO_DOWN:
        u0, u1 = 0.4, 0.6

    v_step = 1 / N_BRICK_COLORS
    v0 = brick.color_index * v_step
    v1 = (brick.color_index + 1) * v_step
    return u0, u1, v0, v1

ANIMATION_DURATION = 0.05
Window.clearcolor = (0, 0, 0, 1)

class CellWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 1) # Black for the grid background
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class BrickWidget(Widget):
    brick_data = ObjectProperty(None)

    def __init__(self, **kwargs):
        # Manually handle brick_data to ensure initialization order is correct
        brick_data_from_kwargs = kwargs.pop('brick_data', None)
        
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        
        # Now that the widget itself is initialized, set up its graphics
        with self.canvas:
            self.bg_rect = Rectangle(source=BRICK_SKIN_PATH)
            
        self.bind(pos=self._update_graphics, size=self._update_graphics)

        # With graphics in place, we can now safely set the data property
        if brick_data_from_kwargs:
            self.brick_data = brick_data_from_kwargs

    def on_brick_data(self, instance, value):
        self._update_visuals()

    def _update_graphics(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def _update_visuals(self):
        if self.brick_data and self.brick_data.intention != CellIntention.VOID:
            u0, u1, v0, v1 = _get_texture_coords(self.brick_data)
            self.bg_rect.tex_coords = [u0, v0, u1, v0, u1, v1, u0, v1]
        else:
            self.bg_rect.tex_coords = [0,0,0,0,0,0,0,0] # Hide texture
        
        self._update_graphics()

class GameWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.is_animating = False
        self._animation_done_callback = None

        # --- Ghost Trail Spawners ---
        self.ghost_spawners = {} # Maps a widget to its Clock event

        # Use a RelativeLayout for robust layering
        game_area_layout = RelativeLayout(size_hint=(0.75, 1))

        # Static grid for background cells
        self.game_grid = GridLayout(cols=FIELD_SIZE, rows=FIELD_SIZE, size_hint=(1, 1), pos_hint={'x':0, 'y':0})
        self.cell_widgets = [[CellWidget() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                self.game_grid.add_widget(self.cell_widgets[r][c])
        
        # Animation layer for moving bricks
        self.animation_layer = FloatLayout(size_hint=(1, 1), pos_hint={'x':0, 'y':0})
        self.brick_widgets = [[None for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]

        game_area_layout.add_widget(self.game_grid)
        game_area_layout.add_widget(self.animation_layer)
        
        self.add_widget(game_area_layout)
        
        self.game_grid.bind(size=self.on_grid_resize, pos=self.on_grid_resize)
        self.game_grid.bind(pos=self.draw_grid_lines, size=self.draw_grid_lines)
        
        # UI Panel
        ui_panel = BoxLayout(orientation='vertical', size_hint=(0.25, 1), spacing=10, padding=10)
        self.score_label = Label(text="Score: 0", size_hint_y=None, height=40)
        level_label = Label(text="Level: 0", size_hint_y=None, height=40)
        self.new_game_button = Button(text="New Game", size_hint_y=None, height=50)
        self.undo_button = Button(text="Undo", size_hint_y=None, height=50)
        self.settings_button = Button(text="Settings", size_hint_y=None, height=50)
        self.diag_label = Label(
            text='Hover over grid...', 
            size_hint_y=None, 
            height=60,
            halign='left',
            valign='top'
        )
        self.diag_label.bind(size=self.diag_label.setter('text_size'))
        ui_panel.add_widget(self.score_label)
        ui_panel.add_widget(level_label)
        ui_panel.add_widget(self.new_game_button)
        ui_panel.add_widget(self.undo_button)
        ui_panel.add_widget(self.settings_button)
        ui_panel.add_widget(self.diag_label)
        ui_panel.add_widget(Widget()) # Spacer
        self.add_widget(ui_panel)

        self.settings_button.bind(on_press=self.open_settings)

        Window.bind(mouse_pos=self.on_mouse_pos)

    def run_after_animation(self, callback):
        """
        Executes a callback function after all current animations are finished.
        If no animations are running, the callback is executed immediately.
        """
        if not self.is_animating:
            callback()
        else:
            self._animation_done_callback = callback

    def open_settings(self, instance):
        from kivy.app import App
        controller = App.get_running_app().controller
        current_settings = {'num_colors': controller.model.num_colors} 
        popup = SettingsPopup(controller, current_settings)
        popup.open()

    def update_score(self, new_score):
        """Updates the score label with the new score."""
        self.score_label.text = f"Score: {new_score}"

    def show_game_over(self, reason):
        """Displays a game-over popup."""
        from kivy.app import App
        controller = App.get_running_app().controller

        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=reason))
        
        popup_new_game_button = Button(text='New Game', size_hint_y=None, height=44)
        content.add_widget(popup_new_game_button)

        popup = Popup(title='Game Over',
                      content=content,
                      size_hint=(None, None), size=('300dp', '200dp'),
                      auto_dismiss=False)
        
        # Bind the button to both the controller's new game method and to dismiss the popup
        popup_new_game_button.bind(on_press=controller.start_new_game)
        popup_new_game_button.bind(on_press=popup.dismiss)
        
        popup.open()

    def on_mouse_pos(self, window, pos):
        if not self.game_grid.collide_point(*pos):
            self.diag_label.text = ""
            return
        
        from kivy.app import App
        controller = App.get_running_app().controller
        r, c = controller.get_coords_from_pos(*pos)
        
        if r is None:
            self.diag_label.text = ""
            return

        model = controller.model
        brick = model.field[r][c]
        color_name = 'N/A'
        if brick.color_index is not None:
            from model import COLOR_NAMES
            color_name = COLOR_NAMES[brick.color_index]
        
        # --- Texture coordinate calculation for diagnostics ---
        u0, u1, v0, v1 = _get_texture_coords(brick)

        diag_text = (f"Coord: ({c}, {r})\n"
                     f"Intention: {brick.intention.name}\n"
                     f"Color: {color_name} ({brick.color_index})\n"
                     f"Skin U: ({u0:.1f}, {u1:.1f}), V: ({v0:.2f}, {v1:.2f})")
        self.diag_label.text = diag_text


    def animate_events(self, removed_coords, moved_coords, on_complete_callback):
        """Animates brick removals and movements."""
        animations_to_run = []

        # --- Removal Animations ---
        for r, c in removed_coords:
            widget = self.brick_widgets[r][c]
            if widget:
                center_x = widget.x + widget.width / 2
                center_y = widget.y + widget.height / 2
                anim = Animation(opacity=0, pos=(center_x, center_y), size=(0, 0), 
                                 duration=ANIMATION_DURATION)
                anim.bind(on_complete=lambda *args, w=widget: self.animation_layer.remove_widget(w))
                animations_to_run.append((anim, widget))
                self.brick_widgets[r][c] = None

        # --- Movement Animations ---
        cell_width = self.game_grid.width / FIELD_SIZE
        cell_height = self.game_grid.height / FIELD_SIZE
        
        model = App.get_running_app().controller.model

        for (start_r, start_c), (end_r, end_c) in moved_coords:
            widget = self.brick_widgets[start_r][start_c]
            if widget:
                # Sync widget with model BEFORE animating
                brick_data_ref = model.field[end_r][end_c]
                widget.brick_data = brick_data_ref
                widget._update_visuals()

                x = end_c * cell_width
                y = (FIELD_SIZE - 1 - end_r) * cell_height
                
                # --- Widget-based Throttled Ghost Trail ---
                anim = Animation(pos=(x, y), duration=ANIMATION_DURATION, t='linear')

                # Capture the brick's state AT THIS MOMENT for the trail
                captured_brick_data = copy.copy(widget.brick_data)

                # Cancel any existing spawner for this widget before creating a new one
                existing = self.ghost_spawners.pop(widget, None)
                if existing is not None:
                    existing.cancel()

                # Schedule the spawner and store the event
                spawner = Clock.schedule_interval(
                    lambda dt: self.spawn_ghost(widget, captured_brick_data), 0.04)
                self.ghost_spawners[widget] = spawner

                # When animation is done, unschedule the spawner
                anim.bind(on_complete=self.on_brick_anim_complete)

                animations_to_run.append((anim, widget))
                
                self.brick_widgets[end_r][end_c] = widget
                self.brick_widgets[start_r][start_c] = None

        if not animations_to_run:
            on_complete_callback()
            return

        self.is_animating = True
        # Use a counter to call the final callback only when all animations are done
        self.animation_counter = len(animations_to_run)

        def _on_animation_complete(*args):
            self.animation_counter -= 1
            if self.animation_counter == 0:
                self.is_animating = False
                # After all animations are done, it's crucial to re-sync with the model
                # to correct any visual inconsistencies from chained moves.
                from kivy.app import App
                model = App.get_running_app().controller.model
                self.draw_field(model.field)
                on_complete_callback()
                if self._animation_done_callback:
                    self._animation_done_callback()
                    self._animation_done_callback = None

        for anim, widget in animations_to_run:
            anim.bind(on_complete=_on_animation_complete)
            anim.start(widget)

    def clear_board_visuals(self):
        """Cancels all animations and removes all bricks from the board."""
        print("DIAG: --- clear_board_visuals START ---")
        # Cancel all scheduled ghost spawners
        for spawner in self.ghost_spawners.values():
            spawner.cancel()
        self.ghost_spawners.clear()

        # Stop all animations on children before clearing them all
        print(f"DIAG: Widgets in animation_layer before clear: {[w.uid for w in self.animation_layer.children if isinstance(w, BrickWidget)]}")
        for widget in self.animation_layer.children:
            if isinstance(widget, BrickWidget):
                Animation.cancel_all(widget)
        self.animation_layer.clear_widgets()
        print(f"DIAG: Widgets in animation_layer after clear: {[w.uid for w in self.animation_layer.children if isinstance(w, BrickWidget)]}")

        # Reset the grid of widget references
        self.brick_widgets = [[None for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]

        # Reset animation state completely
        self.is_animating = False
        self._animation_done_callback = None
        self.animation_counter = 0
        print("DIAG: --- clear_board_visuals END ---")

    def on_brick_anim_complete(self, animation, widget):
        """Called when a brick's movement animation finishes."""
        if widget in self.ghost_spawners:
            self.ghost_spawners[widget].cancel()
            del self.ghost_spawners[widget]

    def spawn_ghost(self, parent_widget, brick_data):
        """Creates a single fading ghost for a trail."""
        ghost = BrickWidget(
            brick_data=brick_data,
            pos=parent_widget.pos,
            size=parent_widget.size,
            opacity=0.6
        )
        self.animation_layer.add_widget(ghost)

        fade_anim = Animation(opacity=0, duration=0.25)
        fade_anim.bind(on_complete=lambda *args, w=ghost: self.animation_layer.remove_widget(w))
        fade_anim.start(ghost)

    def on_grid_resize(self, *args):
        self.update_brick_positions()

    def update_brick_positions(self):
        if not self.game_grid.width > 1:
            return
        cell_width = self.game_grid.width / FIELD_SIZE
        cell_height = self.game_grid.height / FIELD_SIZE
        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                widget = self.brick_widgets[r][c]
                if widget:
                    widget.pos = (c * cell_width, (FIELD_SIZE - 1 - r) * cell_height)
                    widget.size = (cell_width, cell_height)

    def draw_field(self, field_data):
        """Syncs the visual brick widgets with the model's field data."""
        created, updated, removed = [], [], []
        if not self.game_grid.width > 1: # Grid is not drawn yet
            print("DIAG: draw_field: grid not ready, aborting.")
            return

        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                brick_data = field_data[r][c]
                brick_widget = self.brick_widgets[r][c]

                if brick_data.intention != CellIntention.VOID:
                    if brick_widget is None:
                        new_widget = BrickWidget(brick_data=brick_data)
                        self.brick_widgets[r][c] = new_widget
                        self.animation_layer.add_widget(new_widget)
                        created.append((r, c, new_widget.uid))
                    else:
                        brick_widget.brick_data = brick_data
                        updated.append((r, c, brick_widget.uid))
                elif brick_widget is not None:
                    removed.append((r, c, brick_widget.uid))
                    self.animation_layer.remove_widget(brick_widget)
                    self.brick_widgets[r][c] = None

        self.update_brick_positions()
        print(f"DIAG: draw_field: created={len(created)} updated={len(updated)} removed={len(removed)}")
        if created: print(f"DIAG:   created: {created[:8]}{'...' if len(created) > 8 else ''}")
        if removed: print(f"DIAG:   removed: {removed}")

    def sweep_orphan_widgets(self):
        """Removes BrickWidgets present in animation_layer but not tracked in brick_widgets.
        Used by undo to clean up ghost trails and other leftover widgets left by
        interrupted animations."""
        tracked = {self.brick_widgets[r][c]
                   for r in range(FIELD_SIZE)
                   for c in range(FIELD_SIZE)
                   if self.brick_widgets[r][c] is not None}
        swept = []
        for widget in list(self.animation_layer.children):
            if isinstance(widget, BrickWidget) and widget not in tracked:
                Animation.cancel_all(widget)
                spawner = self.ghost_spawners.pop(widget, None)
                if spawner is not None:
                    spawner.cancel()
                self.animation_layer.remove_widget(widget)
                swept.append(widget.uid)
        if swept:
            print(f"DIAG: sweep_orphan_widgets: removed {len(swept)} widgets: {swept[:10]}{'...' if len(swept) > 10 else ''}")

    def draw_grid_lines(self, *args):
        self.game_grid.canvas.after.clear()
        with self.game_grid.canvas.after:
            Color(1, 1, 1, 1)
            grid_x, grid_y = self.game_grid.pos
            grid_w, grid_h = self.game_grid.size
            cell_w = grid_w / FIELD_SIZE
            cell_h = grid_h / FIELD_SIZE
            # Thick boundaries
            y_top = grid_y + grid_h - PLAY_AREA_START * cell_h
            y_bottom = grid_y + grid_h - PLAY_AREA_END * cell_h
            x_left = grid_x + PLAY_AREA_START * cell_w
            x_right = grid_x + PLAY_AREA_END * cell_w
            Line(points=[x_left, y_top, x_right, y_top], width=1.5)
            Line(points=[x_left, y_bottom, x_right, y_bottom], width=1.5)
            Line(points=[x_left, y_top, x_left, y_bottom], width=1.5)
            Line(points=[x_right, y_top, x_right, y_bottom], width=1.5)

            # Thin inner lines
            for c in range(PLAY_AREA_START + 1, PLAY_AREA_END):
                x = grid_x + c * cell_w
                Line(points=[x, y_top, x, y_bottom], width=1)
            for r in range(PLAY_AREA_START + 1, PLAY_AREA_END):
                y = grid_y + grid_h - r * cell_h
                Line(points=[x_left, y, x_right, y], width=1)

class SettingsPopup(Popup):
    def __init__(self, controller, current_settings, **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.current_settings = current_settings

        self.title = 'Settings'
        self.size_hint = (0.6, 0.6)
        self.auto_dismiss = False

        layout = BoxLayout(orientation='vertical', padding=10, spacing=20)

        # --- Difficulty ---
        difficulty_layout = BoxLayout(orientation='vertical', spacing='10dp', size_hint_y=None)
        difficulty_layout.bind(minimum_height=difficulty_layout.setter('height'))

        difficulty_label = Label(text='Difficulty', font_size='20sp', size_hint_y=None, height=40)
        difficulty_layout.add_widget(difficulty_label)

        self.difficulty_checkboxes = {}
        difficulties = {'Easy': 5, 'Medium': 7, 'Hard': 10}
        
        for name, num_colors in difficulties.items():
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
            row.add_widget(Label(text=name, size_hint_x=0.8))
            
            cb = CheckBox(group='difficulty', size_hint_x=0.2)
            cb.active = (self.current_settings.get('num_colors') == num_colors)
            cb.num_colors = num_colors
            self.difficulty_checkboxes[name] = cb
            
            row.add_widget(cb)
            difficulty_layout.add_widget(row)

        layout.add_widget(difficulty_layout)
        layout.add_widget(Widget()) # Spacer

        # --- Buttons ---
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        save_button = Button(text='Save')
        save_button.bind(on_press=self.save_settings)
        cancel_button = Button(text='Cancel')
        cancel_button.bind(on_press=self.dismiss)

        button_layout.add_widget(save_button)
        button_layout.add_widget(cancel_button)

        layout.add_widget(button_layout)
        
        self.content = layout

    def save_settings(self, instance):
        new_settings = {}
        for name, cb in self.difficulty_checkboxes.items():
            if cb.active:
                new_settings['num_colors'] = cb.num_colors
                break
        
        self.controller.apply_settings(new_settings)
        self.dismiss()
