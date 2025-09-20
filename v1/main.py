from kivy.app import App
from model import GameModel
from view import GameWidget
from controller import GameController

class BrickShooterApp(App):
    """
    The main application class that orchestrates the MVC components.
    """
    def build(self):
        """
        Initializes the application, creates and connects the Model, View,
        and Controller.
        """
        model = GameModel()
        view = GameWidget()
        # The controller needs references to the model and view to manage the game
        self.controller = GameController(model, view)
        
        # Perform the initial draw of the game board
        self.controller.start()

        return view

if __name__ == '__main__':
    BrickShooterApp().run()
