from typing import Tuple

class SharedInt():
     def __init__(self, val: int):
          self.val = val

class Assignment():
        def __init__(self, assignees: int = 2, link: "Assignment" = None, offset: int = 0):
            self.assignment = {}
            self.inv_assignment = [None]
            self.curr = SharedInt(1)
            self.assignees = assignees
            self.offset = offset

            if link is not None:
                self.inv_assignment = link.inv_assignment
                self.curr = link.curr

                if self.offset != 0:
                    raise ValueError("Linked Assignments with offset not available")
        
        def get_assignment(self, *args, update: bool = True) -> int:
            ## assignment i, j is from S1 to S2
            assert len(args) == self.assignees, "Incorrect num of arguments"

            curr = self.assignment

            for arg in args[:-1]:
                curr = curr.setdefault(arg, {})
            
            res = curr.setdefault(args[-1], None)

            if res == None:
                if not update: 
                    raise KeyError(f"Attempting to get assignment for {args} when no such assignment exists")
                    del curr[args[-1]]
                    return None
                # set value
                curr[args[-1]] = self.curr.val + self.offset
                self.inv_assignment.append(args)
                self.curr.val += 1
                return curr[args[-1]]
            else:
                # is int
                return res
        
        def get_inv_assignment(self, i: int) -> Tuple[int, int]:
            assert i > self.offset, "invalid choice for i"
            return self.inv_assignment[i - self.offset]