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

## 🎯 How to Play BrickShooter

### The Goal
Clear the entire center playing field completely by shooting colored bricks that will move and create matches of 3 or more bricks of the same color. The center must be totally empty to win!

---

## 🎮 Player's Guide

### Welcome to BrickShooter!
BrickShooter is a strategic puzzle game where you shoot colored bricks to create matches and clear the playing field. It's like a mix of puzzle games and physics-based movement!

### Getting Started
1. **The Playing Field**: The center area (10x10 grid) is your main battlefield where all the action happens
2. **Starting Setup**: Each level begins with some bricks already placed in the center - these form your initial puzzle
3. **Your Ammunition**: Colored bricks around all four edges are your shooting supplies, organized in 3-deep queues for each direction
4. **The Goal**: Clear the entire center area completely - every single brick must be eliminated!

### Choosing Difficulty
Select your challenge level before starting:
- **Easy** (3-4 colors): Great for learning the basics and understanding game mechanics
- **Medium** (5-6 colors): Balanced challenge with room for strategy
- **Hard** (7-10 colors): Maximum difficulty for experienced players

### How to Make Your First Shot
1. **Find Valid Targets**: Look for the darker squares along the very edge of the board (rows 2 and 13, or equivalent positions)
2. **Check the Path**: You can only shoot if there's at least one brick somewhere in that row/column in the center area
3. **Click to Shoot**: Click on an edge square - the game will automatically select and launch the closest available brick
4. **Watch the Action**: Your shot triggers a chain reaction of movement and matching!

### Understanding the Game Flow
After each shot, the game follows this automatic sequence:

1. **Initial Movement**: The shot brick moves toward the center in a straight line
2. **Match Detection**: The game scans for groups of 3+ bricks of the same color in straight lines (horizontal or vertical only)
3. **Match Removal**: All bricks in valid matches disappear instantly
4. **Continued Movement**: Any bricks that can now move (due to cleared spaces) will slide in their intended directions
5. **Repeat**: Steps 2-4 repeat until no more matches or movements are possible

### Types of Bricks You'll Encounter
- **Stationary Bricks**: Fixed in place at level start - these are your primary targets to clear
- **Moving Bricks**: Bricks that slide when shot or when spaces open up
- **All Colors Match**: Any brick can be part of a match, regardless of whether it was originally stationary or moving
- **Edge Crossing**: When moving bricks reach the play area edge, they push into the launch zone, shifting all existing bricks outward and becoming stationary themselves
- **Launch Zone Queue**: Each launch zone has a 3-brick deep queue that provides your shooting ammunition

### Shooting Rules (Important!)
- **Path Requirement**: You can ONLY shoot if there's at least one brick in the center area path
- **Target Space**: The space immediately adjacent to your click must be empty
- **No Empty Shooting**: You cannot shoot into completely empty rows or columns
- **Automatic Selection**: The game picks the closest available brick from your launch zone

### Matching Rules
- **Minimum Group**: Need at least 3 bricks of the same color
- **Straight Lines Only**: Matches must be horizontal or vertical - diagonal doesn't count!
- **Connected Groups**: All matching bricks must be directly connected (no gaps)
- **Simultaneous Clearing**: All bricks in a match disappear at the same time

### Scoring System
- **Base Points**: 10 points per brick cleared
- **Group Bonuses**:
  - 3 bricks: 1x multiplier
  - 4 bricks: 1.5x multiplier
  - 5+ bricks: 2x multiplier
- **Chain Reactions**: Extra points for matches that trigger subsequent matches
- **Efficiency Bonus**: Higher scores for clearing stationary bricks strategically

### Winning and Losing
- **Victory**: Clear the entire center area completely (no bricks remain in the 10x10 play area)
- **Game Over**: No more valid shots available, or the board becomes completely blocked
- **Level Progression**: Beat one level to unlock the next challenge!

### Pro Tips for Success
- **Plan Ahead**: Visualize where your shot will send bricks before clicking
- **Create Cascades**: Position shots to trigger multiple matches in sequence
- **Conserve Ammo**: Look for moves that clear the most bricks per shot
- **Watch Movement Patterns**: Bricks will continue moving after matches - use this to your advantage
- **Edge Management**: Pay attention to how bricks behave when they reach boundaries
- **Color Balance**: Don't let one color dominate - maintain variety for matching opportunities
- **Practice Patience**: Sometimes waiting for the right setup is better than rushing shots

### Common Beginner Mistakes
- **Shooting Blindly**: Always check that your target path has obstacles before shooting
- **Ignoring Movement**: Remember that bricks keep moving after matches clear
- **Diagonal Expectations**: Matches only work in straight horizontal/vertical lines
- **Empty Row Shooting**: Can't shoot into completely empty rows or columns

---

## 🎯 Game Rules & Mechanics

### Objective
Clear the entire play area completely by strategically shooting moving bricks to create matches of 3 or more same-colored bricks in a row. The center must be totally empty to win. The game combines puzzle-solving with physics-based movement mechanics.

### Initial Game Setup
At the start of each level, the center play area is pre-populated with a mix of stationary bricks (that must be cleared) and some colored bricks already in position. The launch zones around the edges contain ammunition bricks ready for shooting.

### Board Layout
The game board is a 16x16 grid divided into distinct zones:

- **Play Area**: Inner 10x10 grid (rows/columns 3-12) - where all action occurs
- **Launch Zones**: Outer 3 rows/columns on each side (rows/columns 0-2 and 13-15) - each zone contains a 3-brick deep queue of ammunition
- **Launch Triggers**: Specific cells in rows/columns 2 and 13 that players click to shoot bricks

### Brick Types & States

#### Brick States (Intentions)
- **`STAND`**: Stationary obstacles that don't move. These are the bricks you need to clear to win.
- **`TO_LEFT`/`TO_RIGHT`/`TO_UP`/`TO_DOWN`**: Moving bricks with directional "gravity" that move one cell per turn toward their intended direction.
- **`VOID`**: Empty cells with no brick.

#### Brick Colors
The game supports up to 10 different colors, with the number of colors determining difficulty level.

### Core Gameplay

#### Shooting Bricks
1. **Launch Triggers**: Click on cells in row 2 or column 2 (or row 13 or column 13) to shoot bricks.
2. **Validation**: The shot is only valid if:
   - The adjacent cell inside the play area is empty (`VOID`)
   - There's at least one obstacle brick in the path from the target cell toward the center (can't shoot into completely empty rows/columns)
   - There's at least one brick in the launch zone path as ammunition
3. **Brick Selection**: The game finds the innermost non-empty brick in the launch zone and gives it directional intention toward the play area.
4. **Direction Assignment**: Shots from the edges give bricks the appropriate movement direction:
   - Top edge (row 2) → `TO_DOWN`
   - Bottom edge (row 13) → `TO_UP`
   - Left edge (column 2) → `TO_RIGHT`
   - Right edge (column 13) → `TO_LEFT`

#### Movement Mechanics
- **Physics-Based Movement**: Bricks with directional intention move one cell per game tick toward their target direction.
- **Collision Detection**: Bricks stop moving when they encounter another brick in their path (regardless of the other brick's intention).
- **Path Blocking**: If a brick's path is blocked, it retains its movement intention and will continue moving if the blocking brick is later removed.
- **Board Crossing**: When moving bricks reach the edge of the play area, they enter the launch zone on that side, pushing all existing bricks in that zone outward (shifting the 3-brick queue) and becoming stationary (`STAND`).

#### Matching System
- **Match Detection**: The game scans for groups of 3 or more orthogonally adjacent bricks of the same color (horizontal or vertical lines only - no diagonal matches).
- **Match Removal**: All bricks in valid matches are immediately removed (become `VOID`).
- **Chain Reactions**: Matches can create new movement opportunities, leading to cascading effects.

#### Resolution Cycle
Every player action triggers an automatic resolution cycle that continues until the board stabilizes:

1. **Match Resolution**: Scan for and remove all valid matches
2. **Movement Resolution**: Move all bricks with directional intention that have clear paths
3. **Board Crossing**: Process bricks that have moved out of the play area
4. **Launch Zone Refill**: Shift bricks inward in 3-deep launch zone queues and add new random-colored bricks to fill empty positions
5. **Repeat**: Continue cycling until no more changes occur

### Scoring System

#### Basic Scoring
- **Base Points**: 10 points per brick removed in a match
- **Group Multipliers**:
  - 3 bricks: 1x multiplier
  - 4 bricks: 1.5x multiplier
  - 5+ bricks: 2x multiplier

#### Advanced Scoring Features
- **Chain Reactions**: Bonus points for matches that trigger subsequent matches
- **Large Groups**: Extra bonuses for clearing large groups of bricks
- **Efficiency Bonus**: Points for clearing stationary bricks efficiently

### Game End Conditions

#### Victory Conditions
- **Level Complete**: The entire play area is completely empty (no bricks of any type remain)
- **Perfect Clear**: Bonus points for clearing the entire board in one continuous chain reaction

#### Game Over Conditions
- **No Valid Moves**: No more shots can be made (blocked launch paths)
- **Board Full**: Play area completely filled with unmatchable bricks
- **Time Limit**: (Future feature) Level time expires

### Strategy & Tips

#### Basic Strategies
1. **Plan Ahead**: Consider how your shot will affect brick movement patterns
2. **Create Cascades**: Position shots to trigger chain reactions
3. **Clear Blockages**: Remove blocking bricks to allow movement
4. **Conserve Ammunition**: Don't waste shots on low-value matches

#### Advanced Tactics
- **Board Crossing**: Use edge movement to reposition difficult bricks
- **Corner Plays**: Utilize corner positions for unique movement opportunities
- **Color Management**: Balance color distribution to maintain matching opportunities
- **Momentum Building**: Create setups that lead to multiple matches per shot

#### Difficulty Levels
- **Easy**: 3-4 colors - perfect for beginners learning the game
- **Medium**: 5-6 colors - balanced gameplay with moderate challenge
- **Hard**: 7-10 colors - maximum challenge for experienced players

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
