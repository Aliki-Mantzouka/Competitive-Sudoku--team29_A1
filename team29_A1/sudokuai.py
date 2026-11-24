#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import random
import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
import competitive_sudoku.sudokuai
from typing import List, Tuple

Square = Tuple[int, int]

# Points awarded for completing 0, 1, 2, or 3 regions in a single move
REGION_POINTS = (0, 1, 3, 7)


def regions_for_square(board: SudokuBoard, square: Square) -> List[List[Square]]:
    row, col = square
    m, n, N = board.m, board.n, board.N

    row_region = [(row, c) for c in range(N)]
    col_region = [(r, col) for r in range(N)]

    block_r0 = (row // m) * m
    block_c0 = (col // n) * n
    block_region = [
        (r, c)
        for r in range(block_r0, block_r0 + m)
        for c in range(block_c0, block_c0 + n)
    ]

    return [row_region, col_region, block_region]

# Count how many regions (0..3) become completely filled by placing `move`
def count_completed_regions_for_move(board: SudokuBoard, move: Move) -> int:
    empty = SudokuBoard.empty
    completed = 0

    for region in regions_for_square(board, move.square):
        # A region is completed if every square except `move.square` is already non-empty
        if all(sq == move.square or board.get(sq) != empty for sq in region):
            completed += 1

    return completed

# Evaluate a game state from `maximizing_player`'s perspective (1 or 2)
def evaluate_state(game_state: GameState, maximizing_player: int) -> float:
    board = game_state.board
    N = board.N
    empty = SudokuBoard.empty

    # Compare our score against the opponent's score
    my_idx = maximizing_player - 1
    opp_idx = 1 - my_idx
    score_diff = float(game_state.scores[my_idx] - game_state.scores[opp_idx])

    # Small bonus for regions that only have 1 or 2 empty cells left
    potential = 0.0
    seen_regions = set()

    for i in range(N):
        for j in range(N):
            for region in regions_for_square(board, (i, j)):
                reg_key = tuple(region)
                if reg_key in seen_regions:
                    continue
                seen_regions.add(reg_key)

                empty_count = sum(1 for sq in region if board.get(sq) == empty)
                if empty_count == 1:
                    potential += 0.25
                elif empty_count == 2:
                    potential += 0.05

    turn_sign = 1.0 if game_state.current_player == maximizing_player else -1.0
    return score_diff + turn_sign * potential

# Order candidate moves from highest impact to lowest so stronger moves are checked first
def order_moves(board: SudokuBoard, moves: List[Move]) -> List[Move]:
    def move_priority(move: Move) -> Tuple[int, int]:
        completed = count_completed_regions_for_move(board, move)
        points = REGION_POINTS[completed] if 0 <= completed < len(REGION_POINTS) else 0
        # Rank by region completion points first, then number of completed regions
        return (points, completed)

    return sorted(moves, key=move_priority, reverse=True)

class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()

    # N.B. This is a very naive implementation.
    def compute_best_move(self, game_state: GameState) -> None:
        N = game_state.board.N

        # Check whether a cell is empty, a value in that cell is not taboo, and that cell is allowed
        def possible(i, j, value):
            return game_state.board.get((i, j)) == SudokuBoard.empty \
                   and not TabooMove((i, j), value) in game_state.taboo_moves \
                       and (i, j) in game_state.player_squares()

        all_moves = [Move((i, j), value) for i in range(N) for j in range(N)
                     for value in range(1, N+1) if possible(i, j, value)]
        move = random.choice(all_moves)
        self.propose_move(move)
        while True:
            time.sleep(0.2)
            self.propose_move(random.choice(all_moves))

