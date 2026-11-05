"""Randomized, food-seeking Snake with a closed-route safety invariant."""
from collections import deque


def random_cycle(base, moves, rng, steps=500):
    # Backbite a Hamiltonian path, keeping only samples whose ends reconnect.
    # Every retained sample is still one cycle through every playable cell.
    path=list(base);best=list(base)
    for _ in range(steps):
        if rng.randrange(2):path.reverse()
        options=[c for c in moves[path[-1]].values() if c is not None and c!=path[-2]]
        other=rng.choice(options);index=path.index(other)
        path=path[:index+1]+list(reversed(path[index+1:]))
        if path[-1] in moves[path[0]].values():best=list(path)
    if rng.randrange(2):best.reverse()
    return best


def choose_next(body, apples, cycle, index, neighbors, rng):
    start=index[body[0]];size=len(cycle)
    distance=lambda c:(index[c]-start)%size
    fallback=cycle[(start+1)%size]
    limit=distance(body[-1])-1
    if apples:limit=min(limit,min(map(distance,apples)))
    candidates=list(dict.fromkeys([fallback]+neighbors(body[0])))
    safe=[c for c in candidates if c is not None and 0<distance(c)<=limit]
    if not safe:return fallback  # This can be the moving tail; growth cannot occur there.
    if not apples:
        # Roam unpredictably while preserving the cyclic order of the body.
        return rng.choices(safe,weights=[1.8 if c==fallback else 1 for c in safe])[0]
    # Multi-source BFS seeks the closest food through currently free cells.
    # This is a preference only: cyclic order/tail clearance above enforce safety.
    blocked=set(body);blocked.discard(body[-1])
    cost={c:0 for c in apples};queue=deque(apples)
    while queue:
        cell=queue.popleft()
        for other in neighbors(cell):
            if other is None or other in blocked or other in cost:continue
            cost[other]=cost[cell]+1;queue.append(other)
    best=min(cost.get(c,1000) for c in safe)
    choices=[c for c in safe if cost.get(c,1000)==best]
    return rng.choices(choices,weights=[1+distance(c)**.5 for c in choices])[0]


def choose_avoiding(body, hazards, neighbors, rng):
    """Prefer open, tail-connected routes when placed hazards break the cycle."""
    candidates=[]
    for head in neighbors(body[0]):
        if head is None or head in hazards or head in list(body)[:-1]:continue
        trail=(head,)+tuple(body)[:-1]
        blocked=set(trail[:-1])|set(hazards);blocked.discard(head)
        reached={head};queue=deque([head])
        while queue:
            for cell in neighbors(queue.popleft()):
                if cell is None or cell in blocked or cell in reached:continue
                reached.add(cell);queue.append(cell)
        # Connectivity to the moving tail is preferable to an open dead end.
        exits=sum(c is not None and c not in hazards and c not in trail[:-1]
                  for c in neighbors(head))
        rank=(trail[-1] in reached,len(reached)>=len(trail),len(reached),exits)
        candidates.append((rank,head))
    if not candidates:return None
    best=max(rank for rank,_ in candidates)
    return rng.choice([cell for rank,cell in candidates if rank==best])
