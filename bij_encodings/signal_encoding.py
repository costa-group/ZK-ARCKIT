"""
DEPRECATED DUE TO LARGE COST
"""
from pysat.formula import CNF
from pysat.card import CardEnc, EncType
from typing import Tuple, Dict, List
from itertools import product
from functools import reduce

from normalisation import r1cs_norm
from r1cs_scripts.circuit_representation import Circuit
from bij_encodings.single_cons_options import signal_options
from bij_encodings.assignment import Assignment

def encode(
        classes:Dict[str, Dict[str, List[int]]],
        in_pair: List[Tuple[str, Circuit]],
        return_signal_mapping: bool = False
    ) -> CNF:
    mapp = Assignment()

    # TODO: ignore 0 signal
    potential = {
        name: {}
        for name, _ in in_pair
    }

    formula = CNF()
    for class_ in classes[in_pair[0][0]].keys():
        if 'n' in class_:

            ## Not exactly 1 canonical form..
            raise NotImplementedError
    
        else:

            ## Collect 'additively' the options within a class
            class_potential = {
                name: {}
                for name, _ in in_pair
            }

            comparisons = product(*[ 
                                    [r1cs_norm(circ.constraints[i])[0] for i in classes[name][class_]] 
                                    for name, circ in in_pair] 
            )

            Options = [
                signal_options(c1, c2)
                for c1, c2 in comparisons
            ]

            Product = [map(
                lambda options : options[name].items(),
                Options
            ) for name, _ in in_pair]

            # Encoding the CNF version of the OR (AND (OR )) results
            # NOTE: takes far too long (too many clauses)
            #   just 1 class of the Sudoku has
            # 913801098372838149144551325521759860813819523132294689800797264287512551573060475601348076193581018372215
            #   8381328415331458530385619301444479156166695333770494995398294763572354075757115645388129442344858615597
            #   2849229050432445143469841764228573597682472525085789026346830294293751385882229073904221388920787182717
            #   8434444632768169400548200960008264947258579041589024973756857056113659812508483880913686882500603274891
            #   7774972952077355889017425770409112268326654809601436501358510613571146745101948954683516686970589584386
            #   5616891955664849607860939326526547194878174766308746421802825715577290853150352303646272960223671268672
            #   2802424981338147789257066203475841049703046497727597832060108728472808863876518455449947411833981036169
            #   0309242603534585195383037827598860879300248915004783141273013382567701249567892085816462762217973430946
            #   2402842823648256883202462812275604480139148664998833236044064948448034866542951750937830468873319595003
            #   3350553521078620016199257483250160986953446425872224649862873145978062888429434399777822789983733338726
            #   0160546624349953591683
            #   clauses

            # Needs very small classes to be viable
            i = 0
            for name in range(2):
                for llist in product(*Product[name]):
                    print(i, end='\r')
                    i += 1

                    lits = reduce(
                        lambda acc, x : acc + [
                            mapp.get_assignment(x[0], j) if name == 0 else mapp.get_assignment(j, x[0])
                            for j in x[1]
                        ],
                        llist,
                        []
                    )

                    if len(lits) == 0:
                        continue

                    formula.extend(
                        CardEnc.atleast(
                            lits = lits,
                            bound = 1,
                            encoding=EncType.pairwise
                        )
                    )           

            #TODO: think about whether the we still intersect accross classes here
            #  -- think it's possible just need to be able to remove clauses -- or add an assumption about non-existent clauses
            
            class_potential = {
                name: {}
                for name, _ in in_pair
            }

            def merge(class_potential, options):
                for name, _ in in_pair:
                    for key in options[name].keys():
                        class_potential[name][key] = class_potential[name].setdefault(key, set([])).union(options[name][key])
                return class_potential
            
            class_potential = reduce(
                merge,
                Options,
                class_potential
            )

            ## Collect 'intersectionally' the options accross classes
            for name, _ in in_pair:
                for signal in class_potential[name].keys():
                    if len(class_potential[name][signal]) == 0:
                        continue
                    potential[name][signal] = potential[name].setdefault(
                                                                signal, class_potential[name][signal]
                                                         ).intersection(
                                                                class_potential[name][signal]
                                                         )
    
    # Internal consistency.
    for (name, _), (oname, _) in zip(in_pair, in_pair[::-1]):
        for signal in potential[name].keys():
            potential[name][signal] = set([
                pair for pair in potential[name][signal]
                    if signal in potential[oname][pair]
            ])

    # Get Removed Options -- i.e. those included in the atleast encodings previous but no longer viable

    removed = reduce(
        lambda acc, key : acc.union( set(mapp.assignment[key].keys()) - potential[in_pair[0][0]][key] ),
        mapp.assignment.Keys(),
        set([])
    )

    # NOTE many sections here not tested due to time of new inner loop.

    for name, _ in in_pair:
        for key in potential[name].keys():
            
            lits = [
                mapp.get_assignment(key, pair) if (name == in_pair[0][0]) else mapp.get_assignment(pair, key)
                for pair in potential[name][key]
            ]

            if lits == []:
                ## Not possible for equivalent circuits -- TODO: check
                return (False, f"Signal {key} in circuit {name} has no potential mapping.")

            formula.extend(
                CardEnc.equals(
                    lits = lits,
                    bound = 1,
                    encoding = EncType.pairwise
                )
            )
    
    return formula if not return_signal_mapping else (formula, mapp)