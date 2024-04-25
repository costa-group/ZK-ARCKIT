from typing import Tuple

class Assignment():
        def __init__(self, offset = 0):
            self.assignment = {}
            self.inv_assignment = [None]
            self.curr = 1 + offset
            self.offset = offset
        
        def get_assignment(self, i: int, j: int) -> int:
            ## assignment i, j is from S1 to S2
            try:
                return self.assignment[i][j]
            except KeyError:
                self.assignment.setdefault(i, {})
                self.assignment[i][j] = self.curr
                self.inv_assignment.append((i, j))
                self.curr += 1
                return self.assignment[i][j]
        
        def get_inv_assignment(self, i: int) -> Tuple[int, int]:
            assert i -self.offset > 0, "invalid choice for i"
            return self.inv_assignment[i - self.offset]