from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.graphics import Color, Rectangle, Triangle, Line
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.properties import ObjectProperty

from model import BRICK_COLORS, FIELD_SIZE, PLAY_AREA_START, PLAY_AREA_END, CellIntention, Brick

BRICK_SKIN_PATH = 'v1/assets/NBricks.bmp'
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
    v0 = 1 - (brick.color_index + 1) * v_step
    v1 = 1 - brick.color_index * v_step
    return u0, u1, v0, v1

ANIMATION_DURATION = 0.02
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
        ui_panel.add_widget(self.diag_label)
        ui_panel.add_widget(Widget()) # Spacer
        self.add_widget(ui_panel)

        Window.bind(mouse_pos=self.on_mouse_pos)

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
                anim = Animation(opacity=0, duration=ANIMATION_DURATION)
                anim.bind(on_complete=lambda *args, w=widget: self.animation_layer.remove_widget(w))
                animations_to_run.append((anim, widget))
                self.brick_widgets[r][c] = None

        # --- Movement Animations ---
        cell_width = self.game_grid.width / FIELD_SIZE
        cell_height = self.game_grid.height / FIELD_SIZE
        
        from kivy.app import App
        model = App.get_running_app().controller.model

        for (start_r, start_c), (end_r, end_c) in moved_coords:
            widget = self.brick_widgets[start_r][start_c]
            if widget:
                # Sync widget with model BEFORE animating
                brick_data = model.field[end_r][end_c]
                widget.brick_data = brick_data
                # Manually trigger the visual update, because Kivy's ObjectProperty
                # won't detect a change if the underlying object is mutated.
                widget._update_visuals()

                x = end_c * cell_width
                y = (FIELD_SIZE - 1 - end_r) * cell_height
                anim = Animation(pos=(x, y), duration=ANIMATION_DURATION)
                animations_to_run.append((anim, widget))
                
                self.brick_widgets[end_r][end_c] = widget
                self.brick_widgets[start_r][start_c] = None

        if not animations_to_run:
            on_complete_callback()
            return

        # Use a counter to call the final callback only when all animations are done
        self.animation_counter = len(animations_to_run)

        def _on_animation_complete(*args):
            self.animation_counter -= 1
            if self.animation_counter == 0:
                # After all animations are done, it's crucial to re-sync with the model
                # to correct any visual inconsistencies from chained moves.
                from kivy.app import App
                model = App.get_running_app().controller.model
                self.draw_field(model.field)
                on_complete_callback()

        for anim, widget in animations_to_run:
            anim.bind(on_complete=_on_animation_complete)
            anim.start(widget)

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
        if not self.game_grid.width > 1: # Grid is not drawn yet
            return

        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                brick_data = field_data[r][c]
                brick_widget = self.brick_widgets[r][c]

                # If there's a brick in the model
                if brick_data.intention != CellIntention.VOID:
                    # If there's no widget for it, create one
                    if brick_widget is None:
                        new_widget = BrickWidget(brick_data=brick_data)
                        self.brick_widgets[r][c] = new_widget
                        self.animation_layer.add_widget(new_widget)
                    # If a widget already exists, update it
                    else:
                        brick_widget.brick_data = brick_data
                
                # If there's no brick in the model, but there is a widget
                elif brick_widget is not None:
                    self.animation_layer.remove_widget(brick_widget)
                    self.brick_widgets[r][c] = None
        self.update_brick_positions()  # Ensure positions/sizes are updated after sync

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
