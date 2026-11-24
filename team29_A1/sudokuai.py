#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

import random
import time
from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
import competitive_sudoku.sudokuai


class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """

    def __init__(self):
        super().__init__()


    def generate_legal_moves(self, game_state: GameState):
        board = game_state.board
        N = board.N
        m = board.m
        n = board.n

        legal_moves = []

        # Get cells allowed for the current player
        allowed_squares = game_state.player_squares()

        # None means all cells are allowed
        if allowed_squares is None:
            allowed_squares = [
                (i, j)
                for i in range(N)
                for j in range(N)
            ]

        # Examine every allowed cell
        for i, j in allowed_squares:

            # Skip cells that are already occupied
            if board.get((i, j)) != SudokuBoard.empty:
                continue

            # Try every possible value
            for value in range(1, N + 1):

                # Exclude taboo moves
                if TabooMove((i, j), value) in game_state.taboo_moves:
                    continue

                # Check Sudoku constraint C0

                # Check row
                if any(board.get((i, col)) == value
                    for col in range(N)):
                    continue

                # Check column
                if any(board.get((row, j)) == value
                    for row in range(N)):
                    continue

                # Check block
                start_row = (i // m) * m
                start_col = (j // n) * n

                block_contains_value = False

                for row in range(start_row, start_row + m):
                    for col in range(start_col, start_col + n):
                        if board.get((row, col)) == value:
                            block_contains_value = True
                            break

                    if block_contains_value:
                        break

                if block_contains_value:
                    continue

                # All conditions satisfied
                legal_moves.append(Move((i, j), value))

        return legal_moves


    def compute_best_move(self, game_state: GameState) -> None:
        legal_moves = self.generate_legal_moves(game_state)

        if not legal_moves:
            return

        self.propose_move(legal_moves[0])