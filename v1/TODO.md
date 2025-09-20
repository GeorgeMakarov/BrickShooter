# BrickShooter Python Rewrite Plan

## Phase 1: Core Architecture & Setup
- [x] **Setup Kivy Project**: Initialize the main application window and basic structure.
- [x] **Define `Brick` Class**: Create the simple data container for `status` and `color`.
- [x] **Define `CellStatus` Enum**: Implement the enum for `STAND`, `TO_LEFT`, `TO_RIGHT`, `TO_UP`, `TO_DOWN`, and `VOID`.
- [x] **Implement `GameEngine`**:
    - [x] Create the 16x16 `self.field` grid.
    - [x] Initialize the grid with `Brick` objects.
- [x] **Implement `CellWidget`**:
    - [x] Create the Kivy widget to represent a single brick.
    - [x] Link its visual appearance (color) to a `Brick` object's state.
- [x] **Implement `GameWidget`**:
    - [x] Create the main Kivy widget to hold the 16x16 grid of `CellWidget`s.
    - [x] Implement the `draw_field` function to render the board based on `GameEngine.field`.

## Phase 2: Game Mechanics - The Resolution Cycle
- [ ] **Implement Match Resolution**:
    - [ ] Scan the 10x10 play area for horizontal groups of 3+ same-colored bricks.
    - [ ] Scan the 10x10 play area for vertical groups of 3+ same-colored bricks.
    - [ ] Change the `status` of matched bricks to `VOID`.
- [x] **Implement Movement Resolution (Step-based)**:
    - [x] Scan all bricks on the board for potential moves.
    - [x] Implement movement logic for bricks moving into `VOID` cells.
    - [ ] Implement collision logic (opposing gravity -> `STAND`).
- [x] **Implement the Main Resolution Cycle Loop**:
    - [x] Create a timer-based loop (`Clock.schedule_interval`) that calls a `resolution_step` function.
    - [x] The loop continues as long as movement or matches occur.

## Phase 3: Player Interaction
- [ ] **Handle Player Input**:
    - [x] Detect taps on `CellWidget`s.
    - [x] Pass tap coordinates to the `GameEngine`.
- [x] **Implement "Shoot Brick" Use-Case**:
    - [x] Validate tap is in a "launch trigger row".
    - [x] Find the correct ammunition brick in the launch zone.
    - [x] Assign the correct directional `status` to the brick.
    - [x] Trigger the Resolution Cycle (stubbed).

## Phase 4: Game Flow & UI
- [ ] **Implement `new_game` Logic**:
    - [ ] Populate the play area with `STAND` bricks for a new level.
    - [x] Populate the launch zones with ammunition bricks.
- [ ] **Implement Scoring System**:
    - [ ] Add a score variable to `GameEngine`.
    - [ ] Increment score when bricks are matched and deleted.
    - [x] Display the score in the UI.
- [ ] **Implement Game State Checks**:
    - [ ] Check for "Level Complete" (e.g., no `STAND` bricks left).
    - [ ] Check for "Game Over" (e.g., no more moves possible).
- [ ] **Connect UI Buttons**:
    - [ ] Make the "New Game" button call `new_game`.
    - [ ] Implement and connect an "Undo" button (optional, can be complex).
