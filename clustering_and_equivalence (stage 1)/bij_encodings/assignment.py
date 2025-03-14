from typing import Tuple

"""
Class container for the a key mapping for a set of values
"""

class SharedInt():
    """Container for a shared integer. Allows multiple pointer to always point to the same int"""
    def __init__(self, val: int):
        self.val = val

class Assignment():
        """
        Class Constainer for mapping tuples of input keys to values

        Attributes
        -----------
            assignment: Dict^{assignees}[any, int]
                A dictionary of dictionaries recurring `assignees` number of times. Mapping the tuple of keys
                to a integer value
            inv_assignment: List[Tuple[any]]
                The inverse mapping of assignment
            curr: SharedInt
                The value of the next new assignment
            assignees: int
                The input tuple for the assignment dictionary.
            offset: int
                The any returned value will be given the offset
        """        

        def __init__(self, assignees: int = 2, link: "Assignment" = None, offset: int = 0):
            """
            Constructor for Assignment class

            Parameters
            -----------
                assignees: int
                    The input tuple for the assignment dictionary. Default 2.
                link: Assignment | None
                    If link is not None, the two assignments will never use the same value.
                    They will share curr, and inv_assignment but not assignment.
                    Default None. If link is not None offset must be 0
                offset: int
                    The any returned value will be given the offset
            """    
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
            """
            For a given tuple input, finds and returns a mapping to a value. 
            Caching the value if it wasn't previously.

            Parameters
            ----------
                *args: Tuple[int]
                    The tuple of args to be mapped. Must be of length self.assignees
                update: Bool
                    Whether to cache the resultant value if no mapping exists. Default True
            
            Returns
            ---------
            int
                The value stored in the dictionary for the input args
            
            Raises
            ---------
            KeyError
                Call with update is False and no cached mapping value.
            """

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
            """
            Returns inverse mapping of value i
            
            Returns
            ---------
            Tuple[any]
                Input tuple of inverse mapping i. With be of length self.assignees
            
            Raises
            ---------
            AssertionError
                Call with value <= self.offset
            """

            assert i > self.offset, f"Input index {i} <= {self.offset}"
            return self.inv_assignment[i - self.offset]