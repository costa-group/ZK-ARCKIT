from typing import Tuple

class Assignment():
        def __init__(self, offset = 0, assignees: int = 2):
            self.assignment = {}
            self.inv_assignment = [None]
            self.curr = 1 + offset
            self.offset = offset
        
        def get_assignment(self, *args) -> int:
            ## assignment i, j is from S1 to S2
            curr = self.assignment

            for arg in args[:-1]:
                curr = curr.setdefault(arg, {})
            
            res = curr.setdefault(args[-1], None)


            if res == None:
                # set value
                curr[args[-1]] = self.curr
                self.inv_assignment.append(args)
                self.curr += 1
                return curr[args[-1]]
            else:
                # is int
                return res
        
        def get_inv_assignment(self, i: int) -> Tuple[int, int]:
            assert i -self.offset > 0, "invalid choice for i"
            return self.inv_assignment[i - self.offset]