#  (C) Copyright Wieger Wesselink 2021. Distributed under the GPL-3.0-or-later
#  Software License, (See accompanying file LICENSE or copy at
#  https://www.gnu.org/licenses/gpl-3.0.txt)

from competitive_sudoku.sudoku import GameState, Move, SudokuBoard, TabooMove
import competitive_sudoku.sudokuai

# Points for completing 0, 1, 2 or 3 regions with a single move.
POINTS = [0, 1, 3, 7]
INF = float("inf")

class SudokuAI(competitive_sudoku.sudokuai.SudokuAI):
    """
    Sudoku AI that computes a move for a given sudoku configuration.
    """
    def __init__(self):
        super().__init__()

    # N.B. This is a very naive implementation.

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
        # We are the maximizing player for the whole search.
        self.me = game_state.current_player

        legal_moves = self.generate_legal_moves(game_state)

        if not legal_moves:
            return

        self.propose_move(legal_moves[0])

        # Iterative deepening: search 1, 2, 3, ... moves ahead and propose the best
        # move after every completed depth. The framework stops this method when
        # the time for the turn is up; the last proposed move is the one played.
        depth = 1
        while depth <= self.count_empty(game_state):
            best_move = self.search_root(game_state, legal_moves, depth)
            self.propose_move(best_move)
            # Search the current best move first next time: this gives more pruning.
            legal_moves.remove(best_move)
            legal_moves.insert(0, best_move)
            depth += 1


    def evaluate(self, game_state: GameState):
        """Our score minus the opponent's score (higher = better for us)."""
        return game_state.scores[self.me - 1] - game_state.scores[2 - self.me]

    

    def search_root(self, game_state: GameState, moves, depth):
        """minimax() returns a score, not a move, so the root keeps track of which move scored best."""
        best_value, best_move = -INF, moves[0]
        alpha, beta = -INF, INF
        for move in moves:
            points = self.apply_move(game_state, move)  # game_state is now the child
            value = self.minimax(game_state, depth - 1, alpha, beta, False)
            self.undo_move(game_state, move, points)  # back to the original position
            if value > best_value:
                best_value, best_move = value, move
            alpha = max(alpha, value)
        return best_move

    def minimax(self, game_state: GameState, depth, alpha, beta, maximizing_player):
        """Value of `game_state` for us, looking `depth` moves ahead."""
        if depth == 0 or self.count_empty(game_state) == 0:
            return self.evaluate(game_state)

        children = self.order_moves(game_state, self.generate_legal_moves(game_state))

        # A player with no allowed cell skips their turn.
        if not children:
            self.skip_turn(game_state)
            value = self.minimax(game_state, depth - 1, alpha, beta, not maximizing_player)
            self.skip_turn(game_state)
            return value

        if maximizing_player:
            max_eval = -INF
            for move in children:
                points = self.apply_move(game_state, move)
                evaluation = self.minimax(game_state, depth - 1, alpha, beta, False)
                self.undo_move(game_state, move, points)
                max_eval = max(max_eval, evaluation)
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break  # the opponent will never allow this line
            return max_eval
        else:
            min_eval = INF
            for move in children:
                points = self.apply_move(game_state, move)
                evaluation = self.minimax(game_state, depth - 1, alpha, beta, True)
                self.undo_move(game_state, move, points)
                min_eval = min(min_eval, evaluation)
                beta = min(beta, evaluation)
                if beta <= alpha:
                    break  # we already have a better option elsewhere
            return min_eval

    
    def order_moves(self, game_state: GameState, moves):
        """Put moves that complete a region first, so alpha-beta can prune more."""
        board = game_state.board
        completes = {}

        def key(move):
            if move.square not in completes:
                completes[move.square] = self.completes_region(board, move.square)
            return not completes[move.square]  # False (= completes a region) sorts first

        return sorted(moves, key=key)

    def apply_move(self, game_state: GameState, move):
        """Play `move` on `game_state` in place (it becomes the child). Returns the points scored."""
        board = game_state.board
        player = game_state.current_player
        board.put(move.square, move.value)
        completed = sum(all(board.get(s) != SudokuBoard.empty for s in region)
                        for region in self.region_squares(board, move.square))
        points = POINTS[completed]
        game_state.scores[player - 1] += points
        occupied = self.occupied_squares(game_state, player)
        if occupied is not None:
            occupied.append(move.square)  # the cell now belongs to this player
        game_state.current_player = 3 - player
        return points

    def undo_move(self, game_state: GameState, move, points):
        """Exactly reverse apply_move()."""
        game_state.current_player = 3 - game_state.current_player
        player = game_state.current_player
        occupied = self.occupied_squares(game_state, player)
        if occupied is not None:
            occupied.pop()
        game_state.scores[player - 1] -= points
        game_state.board.put(move.square, SudokuBoard.empty)

    def skip_turn(self, game_state: GameState):
        game_state.current_player = 3 - game_state.current_player

    def occupied_squares(self, game_state: GameState, player):
        return game_state.occupied_squares1 if player == 1 else game_state.occupied_squares2

    def region_squares(self, board, square):
        """The squares of the row, the column and the block that contain `square`."""
        N, m, n = board.N, board.m, board.n  # same block convention as generate_legal_moves
        i, j = square
        start_row = (i // m) * m
        start_col = (j // n) * n
        row = [(i, col) for col in range(N)]
        column = [(row, j) for row in range(N)]
        block = [(row, col) for row in range(start_row, start_row + m)
                 for col in range(start_col, start_col + n)]
        return row, column, block

    def completes_region(self, board, square):
        """True if `square` is the last empty cell of its row, column or block."""
        return any(all(board.get(s) != SudokuBoard.empty for s in region if s != square)
                   for region in self.region_squares(board, square))

    def count_empty(self, game_state: GameState):
        board = game_state.board
        return sum(board.get((i, j)) == SudokuBoard.empty
                   for i in range(board.N) for j in range(board.N))