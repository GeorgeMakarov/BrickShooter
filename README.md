# BrickShooter

A Python-based puzzle game built with Kivy, featuring a unique brick-shooting mechanic with physics-based movement and match-3 gameplay.

## 🎮 Game Overview

BrickShooter is a strategic puzzle game where players shoot colored bricks into a play area to create matches of 3 or more same-colored bricks. The game features:

- **16x16 game board** with a 10x10 play area surrounded by launch zones
- **Physics-based movement** where bricks move according to their "intention" (gravity)
- **Match-3 mechanics** for scoring and brick removal
- **Strategic gameplay** requiring careful planning of shots
- **Animated visual effects** with ghost trails and smooth transitions

## 🏗️ Architecture

The game follows a **Model-View-Controller (MVC)** pattern:

- **Model** (`model.py`): Game state, brick data, and game logic
- **View** (`view.py`): Kivy-based UI components and visual rendering
- **Controller** (`controller.py`): Input handling and game flow coordination

### Key Components

- **`Brick`**: Data container for brick state (intention, color)
- **`GameModel`**: Core game logic and state management
- **`GameWidget`**: Main UI container with grid and controls
- **`BrickWidget`**: Individual brick visual representation
- **`GameController`**: Orchestrates interactions between model and view

## 🎯 Game Mechanics

### Board Layout
- **Play Area**: Inner 10x10 grid where matches occur
- **Launch Zones**: Outer 3 rows/columns on each side containing ammunition
- **Brick States**: `VOID`, `STAND`, `TO_LEFT`, `TO_RIGHT`, `TO_UP`, `TO_DOWN`

### Core Gameplay
1. **Shooting**: Click on launch trigger cells to fire bricks into the play area
2. **Movement**: Bricks with directional intention move one cell per game tick
3. **Matching**: Groups of 3+ same-colored bricks are removed and scored
4. **Resolution Cycle**: Automatic processing of movement and matches until stable

### Scoring System
- Base score: 10 points per brick in a match
- Bonus multiplier for larger groups
- Progressive difficulty with more colors

## 🚀 Getting Started

### Prerequisites
- Python 3.7+
- Kivy framework

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd BrickShooter
   ```

2. **Install dependencies**:
   ```bash
   pip install -r v1/requirements.txt
   ```

3. **Run the game**:
   ```bash
   cd v1
   python main.py
   ```

### Controls
- **Mouse**: Click on launch trigger cells (rows/columns 2 and 13) to shoot bricks
- **New Game**: Start a fresh game
- **Undo**: Revert to previous game state
- **Settings**: Adjust difficulty (number of colors)

## 📁 Project Structure

```
BrickShooter/
├── v1/                          # Python implementation
│   ├── main.py                  # Application entry point
│   ├── model.py                 # Game logic and state
│   ├── view.py                  # UI components
│   ├── controller.py            # Input handling
│   ├── requirements.txt         # Dependencies
│   ├── DESIGN.md               # Technical design document
│   ├── TODO.md                 # Development roadmap
│   └── assets/                 # Game assets
│       ├── bricks.bmp          # Brick texture
│       └── NBricks.bmp         # Alternative brick texture
├── Broker/                     # Legacy Pascal implementation
└── README.md                   # This file
```

## 🎨 Visual Features

- **Animated brick movement** with smooth transitions
- **Ghost trail effects** during brick movement
- **Texture-based rendering** with multiple brick colors
- **Grid visualization** with play area boundaries
- **Real-time diagnostics** showing brick properties on hover

## 🔧 Development Status

### ✅ Completed Features
- Core MVC architecture
- Brick shooting mechanics
- Movement resolution system
- Match detection and removal
- Animated visual effects
- Game state management
- Settings and difficulty options

### 🚧 In Progress
- Level progression system
- Advanced scoring mechanics
- Game over conditions
- Performance optimizations

### 📋 Planned Features
- Sound effects and music
- Particle effects
- Level editor
- High score system
- Multiplayer support

## 🛠️ Technical Details

### Game Loop
1. **Input Processing**: Handle player clicks on launch zones
2. **Shot Validation**: Check if shot is valid (clear path, ammunition available)
3. **Resolution Cycle**: Process movement and matches until stable
4. **Board Updates**: Refill launch zones and check game state

### Animation System
- **Movement animations** with linear interpolation
- **Ghost trail spawning** during brick movement
- **Fade effects** for brick removal
- **Synchronized updates** between model and view

### Performance Considerations
- **Efficient collision detection** for movement validation
- **Optimized rendering** with texture atlasing
- **Memory management** for animation objects
- **State synchronization** between model and view

## 🐛 Known Issues

- Some edge cases in board-crossing logic
- Animation synchronization during rapid moves
- Memory usage with long gameplay sessions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source. Please check the license file for details.

## 🎯 Future Roadmap

- **Phase 1**: Core gameplay completion
- **Phase 2**: Enhanced visual effects
- **Phase 3**: Advanced features (levels, scoring)
- **Phase 4**: Polish and optimization

---

*Built with ❤️ using Python and Kivy*
