# BrickShooter Game Design Document

## 1. Core Architecture

The game follows a Model-View-Controller (MVC) like pattern:

-   **Model (The Game State)**: The `self.field` grid in the `GameEngine`. It is a 16x16 2D array of `Brick` objects. The `Brick` class is a simple data container holding `status` and `color`. It has no logic.
-   **View (The UI)**: The Kivy `CellWidget` grid. Its only job is to visually represent the state of the `Brick` objects. It displays the correct color for a brick and will eventually handle animations.
-   **Controller (The Game Engine)**: The `GameEngine` (currently part of `GameWidget`) is the central brain. It owns the game state and contains all the game logic. It responds to player input and orchestrates all changes to the game state, then updates the view.

### Control Flow

1.  The **Player** interacts with the **View** (`CellWidget`).
2.  The **View** notifies the **Controller** (`GameEngine`) of the interaction (e.g., "cell (2, 5) was tapped").
3.  The **Controller** processes the input and modifies the **Model** (`Brick` objects in the `self.field` grid) according to the game rules.
4.  The **Controller** triggers the **View** to redraw itself based on the updated **Model**.

---

## 2. Game Mechanics and Rules

### 2.1. The Game Board

-   The board is a 16x16 grid.
-   **Play Area**: The inner 10x10 grid (indices 3 to 12).
-   **Launch Zones**: The outer three rows/columns on each side (indices 0-2 and 13-15). Bricks in these zones are the "ammunition" for the player.

### 2.2. Brick States (`CellStatus` Enum)

The `status` of a brick defines its **intent** or **gravity**.

-   **`STAND`**: The brick is stationary and has no gravity. It acts as a permanent obstacle unless it is part of a matched group and gets deleted. These are primarily the bricks placed at the start of a level.
-   **`TO_LEFT`, `TO_RIGHT`, `TO_UP`, `TO_DOWN`**: The brick has "gravity" and intends to move in the specified direction. It will move one cell per game tick if the target cell is empty.
-   **`VOID`**: The cell is empty.

### 2.3. Core Game Loop: The Resolution Cycle

The game is turn-based from the player's perspective, but the consequences of a move are resolved in a **Resolution Cycle**. This cycle runs repeatedly after every player action until the board state is stable (no more changes are possible).

**Trigger**: A player successfully launches a brick.

**Cycle Steps**:
1.  **Match Resolution**:
    -   The engine scans the entire play area for groups of 3 or more adjacent, non-`VOID` bricks of the same color.
    -   All bricks in a valid group have their `status` changed to `VOID`.
    -   The score is updated.
2.  **Movement Resolution**:
    -   The engine scans every brick on the board.
    -   For each brick with a directional `status` (e.g., `TO_RIGHT`):
        -   **Collision Check**: It checks the adjacent cell in its direction of gravity. If that cell is occupied by another brick (regardless of that brick's intention), its path is blocked and it will not move this tick. Its movement intention is preserved. If the blocking brick is later removed (e.g. by a match), this brick will continue moving as intended.
        -   **Movement Check**: If the adjacent cell is `VOID`, the engine "moves" the brick by swapping the `Brick` object in the grid with the `VOID` one.
        -   **Cross-Board Travel**: If a moving brick reaches the far edge of the board, it enters the launch zone on that side, pushing the existing bricks and taking the last available spot.
3.  **Loop Continuation**: If any brick was moved or deleted during this cycle, the cycle runs again from Step 1.
4.  **Loop End**: If a full cycle completes with no matches and no movements, the board is stable, and the engine waits for the next player input.

---

## 3. Use-Cases

### Use-Case: Player Shoots a Brick

-   **Actor**: Player
-   **Trigger**: Player taps a cell in a "launch trigger row" (row/col 2 or 13).
-   **Pre-condition**: 
    1. The cell in the play area immediately adjacent to the tapped cell must be `VOID`.
    2. There must be at least one non-`VOID` brick somewhere along the launch path within the play area. A brick cannot be launched into an entirely empty row or column.
-   **Sequence**:
    1.  `GameEngine` receives the coordinates of the tap (e.g., `(2, 5)`).
    2.  It validates that it's a valid launch trigger cell.
    3.  It checks the adjacent cell inside the play area (e.g., `(3, 5)`).
    4.  If the adjacent cell is **not** `VOID`, the action fails. Nothing happens.
    5.  It then checks the rest of the path in the launch direction. If the entire path is `VOID`, the action fails.
    6.  If the path is valid, the engine finds the first non-`VOID` brick in that row/column within the launch zone, searching from the inside-out (from row/col 2 or 13 outwards).
    7.  It assigns that brick a "gravity" (`status`) pointing into the play area (e.g., a tap at `(2, 5)` gives the brick at `(2, 5)` a `TO_DOWN` status).
    8.  The `GameEngine` initiates the **Resolution Cycle**.

### Use-Case: The Full Resolution Cycle

This is the sequence of events that happens automatically after a player successfully launches a brick.

1.  **Start Animated Loop**: The engine starts a timer (`Clock.schedule_interval`) that executes one "resolution step" every fraction of a second.
2.  **Movement Step**: In each step, the engine scans the entire 16x16 grid.
    -   Any brick with a directional `status` that is adjacent to a `VOID` cell in its path is moved into that `VOID` cell.
    -   If any bricks moved during this step, the loop continues.
3.  **Check for Stability**: If a full movement step occurs where **no bricks move**, the animated loop stops. The board is temporarily stable.
4.  **Process Board-Crossers**: The engine now checks the perimeter of the play area for bricks that have crossed the board.
    -   Example: A brick at `(12, 5)` with `status=TO_RIGHT` has hit the edge.
    -   The engine shifts the entire destination ammunition queue over by one (e.g., brick at `(14,5)` -> `(15,5)`, `(13,5)` -> `(14,5)`). The outermost brick is discarded.
    -   The crossing brick is placed in the now-empty innermost launch cell (e.g., `(13,5)`), and its status is set to `STAND`.
    -   If any bricks were processed this way, the cycle goes back to **Step 1** and starts a new animated loop, as the board state has changed.
5.  **Refill Launch Zones**: If the board was stable and **no bricks crossed the board**, the engine refills the ammunition queues.
    -   For every one of the 40 launch queues (e.g., row 5, cols `2, 1, 0`):
    -   The engine scans from the inside-out for `VOID` cells.
    -   If a `VOID` is found, it shifts the outer bricks inwards to fill the gap (e.g., brick at col `0` moves to `1`).
    -   If the outermost cell is now `VOID`, a new, random-colored `STAND` brick is created in its place.
    -   If any bricks were shifted or refilled, the cycle goes back to **Step 1** and starts a new animated loop.
6.  **Final State**: If the board is stable, no bricks crossed, and no launch zones needed refilling, the resolution cycle is truly complete. The engine now waits for the next player input.
