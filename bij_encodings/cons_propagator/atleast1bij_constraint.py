from typing import List, Dict

from bij_encodings.cons_propagator.singlebij_constraint import ConsBijConstraint

class ConsAtLeast1BijConstraint():
    def __init__(self, bijconstraints: List[ConsBijConstraint], in_pair):
        
        self.cons = bijconstraints

        pass

    def attach_values(self, values) -> None:
        pass

    def register_watched(self, to_watch) -> None:
        pass

    def propagate(self, lit: int = None) -> List[int]:
        pass

    def justify(self, lit: int) -> List[int]:
        pass

    def abandon(self, lit: int) -> List[int]:
        pass

    def falsified_by(self, model: Dict[int, int]) -> bool:
        pass

    def explain_failure(self):
        pass