# Group: [Your Group Number]
# Date: 2026-03-16
# Members: [Names]

from mesa import Agent
from objects import Waste, Radioactivity, WasteDisposal


# ---------------------------------------------------------------------------
# Helper: move one step toward a target, respecting zone boundaries
# ---------------------------------------------------------------------------

def _move_toward(pos, target, min_x, max_x, grid_height):
    """Return a move action dict toward target within allowed x range."""
    x, y = pos
    tx, ty = target
    candidates = []

    if tx > x and x + 1 <= max_x:
        candidates.append((1, 0))
    if tx < x and x - 1 >= min_x:
        candidates.append((-1, 0))
    if ty > y and y + 1 < grid_height:
        candidates.append((0, 1))
    if ty < y and y - 1 >= 0:
        candidates.append((0, -1))

    if not candidates:
        return {"type": "wait"}

    # prefer the axis with greater distance
    candidates.sort(key=lambda d: -(abs(tx - (x + d[0])) + abs(ty - (y + d[1]))),
                     reverse=True)
    # actually, sort so we pick the direction that reduces distance most
    candidates.sort(key=lambda d: abs(tx - (x + d[0])) + abs(ty - (y + d[1])))
    dx, dy = candidates[0]
    return {"type": "move", "dx": dx, "dy": dy}


def _nearest_unvisited(pos, visited, min_x, max_x, grid_height):
    """Find nearest unvisited tile within allowed zone."""
    best = None
    best_dist = float("inf")
    for cx in range(min_x, max_x + 1):
        for cy in range(grid_height):
            if (cx, cy) not in visited:
                dist = abs(cx - pos[0]) + abs(cy - pos[1])
                if dist < best_dist:
                    best_dist = dist
                    best = (cx, cy)
    return best


def _random_move(pos, min_x, max_x, grid_height, rng):
    """Pick a random valid direction within zone bounds."""
    directions = []
    x, y = pos
    if x + 1 <= max_x:
        directions.append((1, 0))
    if x - 1 >= min_x:
        directions.append((-1, 0))
    if y + 1 < grid_height:
        directions.append((0, 1))
    if y - 1 >= 0:
        directions.append((0, -1))
    if not directions:
        return {"type": "wait"}
    dx, dy = rng.choice(directions)
    return {"type": "move", "dx": dx, "dy": dy}


# ---------------------------------------------------------------------------
# Base Robot Agent
# ---------------------------------------------------------------------------

class RobotAgent(Agent):
    """Base class for all robot agents."""

    def __init__(self, model, min_x, max_x):
        super().__init__(model)
        self.min_x = min_x
        self.max_x = max_x
        self.knowledge = {
            "pos": None,
            "inventory": [],
            "visited": set(),
            "known_wastes": {},   # {(x,y): set of waste_types}
            "neighbors": {},      # from last percepts
            "disposal_pos": None,
            "min_x": min_x,
            "max_x": max_x,
            "grid_height": model.grid.height,
            "holding_since": 0,   # steps since last inventory change
            "step_count": 0,
        }
        self.percepts = None  # will be set after first do()

    # --- Percept-Deliberate-Act loop ---

    def step(self):
        self._update_knowledge(self.percepts)
        action = self.deliberate(self.knowledge)
        self.percepts = self.model.do(self, action)

    def _update_knowledge(self, percepts):
        k = self.knowledge
        k["pos"] = self.pos
        k["step_count"] += 1

        if percepts is None:
            # First step: build percepts from current surroundings
            percepts = self.model.get_percepts(self)

        k["visited"].add(k["pos"])

        # Update neighbor info and known wastes
        k["neighbors"] = percepts
        for cell_pos, contents in percepts.items():
            waste_types = contents.get("wastes", [])
            if waste_types:
                k["known_wastes"][cell_pos] = set(waste_types)
            else:
                k["known_wastes"].pop(cell_pos, None)

            if contents.get("disposal", False):
                k["disposal_pos"] = cell_pos

    def deliberate(self, knowledge):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Green Robot
# ---------------------------------------------------------------------------

class GreenAgent(RobotAgent):
    """Operates in z1. Picks 2 green -> transforms to 1 yellow -> transports east."""

    def __init__(self, model, max_x):
        super().__init__(model, min_x=0, max_x=max_x)

    def deliberate(self, k):
        pos = k["pos"]
        inv = k["inventory"]
        neighbors = k["neighbors"]
        max_x = k["max_x"]
        min_x = k["min_x"]
        gh = k["grid_height"]

        green_count = inv.count("green")
        yellow_count = inv.count("yellow")

        # 1. Transform if holding 2 green
        if green_count >= 2:
            return {"type": "transform", "from": "green", "to": "yellow"}

        # 2. If holding yellow waste, transport east and drop at boundary
        if yellow_count > 0:
            if pos[0] >= max_x:
                return {"type": "drop", "waste_type": "yellow"}
            return _move_toward(pos, (max_x, pos[1]), min_x, max_x, gh)

        # 3. If standing on green waste, pick it up
        if pos in neighbors:
            cell_wastes = neighbors[pos].get("wastes", [])
            if "green" in cell_wastes and green_count < 2:
                return {"type": "pick_up", "waste_type": "green"}

        # 4. Move toward nearest known green waste
        green_positions = [
            p for p, types in k["known_wastes"].items()
            if "green" in types and min_x <= p[0] <= max_x
        ]
        if green_positions:
            nearest = min(green_positions, key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1]))
            return _move_toward(pos, nearest, min_x, max_x, gh)

        # 5. If holding 1 green, no known green waste, and fully explored:
        #    go to center of zone and drop it (aggregation point)
        if green_count == 1:
            unvisited = _nearest_unvisited(pos, k["visited"], min_x, max_x, gh)
            if unvisited is None:
                center = ((min_x + max_x) // 2, gh // 2)
                if pos == center:
                    return {"type": "drop", "waste_type": "green"}
                return _move_toward(pos, center, min_x, max_x, gh)

        # 6. Explore unvisited tiles
        target = _nearest_unvisited(pos, k["visited"], min_x, max_x, gh)
        if target:
            return _move_toward(pos, target, min_x, max_x, gh)

        # 7. Random move
        return _random_move(pos, min_x, max_x, gh, self.random)


# ---------------------------------------------------------------------------
# Yellow Robot
# ---------------------------------------------------------------------------

class YellowAgent(RobotAgent):
    """Operates in z1+z2. Picks 2 yellow -> transforms to 1 red -> transports east."""

    def __init__(self, model, max_x):
        super().__init__(model, min_x=0, max_x=max_x)

    def deliberate(self, k):
        pos = k["pos"]
        inv = k["inventory"]
        neighbors = k["neighbors"]
        max_x = k["max_x"]
        min_x = k["min_x"]
        gh = k["grid_height"]

        yellow_count = inv.count("yellow")
        red_count = inv.count("red")

        # 1. Transform if holding 2 yellow
        if yellow_count >= 2:
            return {"type": "transform", "from": "yellow", "to": "red"}

        # 2. If holding red waste, transport east and drop at boundary
        if red_count > 0:
            if pos[0] >= max_x:
                return {"type": "drop", "waste_type": "red"}
            return _move_toward(pos, (max_x, pos[1]), min_x, max_x, gh)

        # 3. If standing on yellow waste, pick it up
        if pos in neighbors:
            cell_wastes = neighbors[pos].get("wastes", [])
            if "yellow" in cell_wastes and yellow_count < 2:
                return {"type": "pick_up", "waste_type": "yellow"}

        # 4. Move toward nearest known yellow waste
        yellow_positions = [
            p for p, types in k["known_wastes"].items()
            if "yellow" in types and min_x <= p[0] <= max_x
        ]
        if yellow_positions:
            nearest = min(yellow_positions, key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1]))
            return _move_toward(pos, nearest, min_x, max_x, gh)

        # 5. If holding 1 yellow, no known yellow waste, and fully explored:
        #    go to center of zone and drop it (aggregation point)
        if yellow_count == 1:
            unvisited = _nearest_unvisited(pos, k["visited"], min_x, max_x, gh)
            if unvisited is None:
                center = ((min_x + max_x) // 2, gh // 2)
                if pos == center:
                    return {"type": "drop", "waste_type": "yellow"}
                return _move_toward(pos, center, min_x, max_x, gh)

        # 6. Explore unvisited tiles
        target = _nearest_unvisited(pos, k["visited"], min_x, max_x, gh)
        if target:
            return _move_toward(pos, target, min_x, max_x, gh)

        # 7. Random move
        return _random_move(pos, min_x, max_x, gh, self.random)


# ---------------------------------------------------------------------------
# Red Robot
# ---------------------------------------------------------------------------

class RedAgent(RobotAgent):
    """Operates in z1+z2+z3. Picks 1 red -> transports to disposal zone."""

    def __init__(self, model, max_x):
        super().__init__(model, min_x=0, max_x=max_x)

    def deliberate(self, k):
        pos = k["pos"]
        inv = k["inventory"]
        neighbors = k["neighbors"]
        max_x = k["max_x"]
        min_x = k["min_x"]
        gh = k["grid_height"]

        red_count = inv.count("red")
        disposal = k["disposal_pos"]

        # 1. If holding red waste and on disposal zone, drop it
        if red_count > 0 and disposal and pos == disposal:
            return {"type": "drop", "waste_type": "red"}

        # 2. If holding red waste, move toward disposal
        if red_count > 0 and disposal:
            return _move_toward(pos, disposal, min_x, max_x, gh)

        # 3. If holding red waste but disposal unknown, explore east column
        if red_count > 0:
            # If already at east edge, scan up/down to find disposal
            if pos[0] >= max_x:
                # Try unvisited cells in the east column
                for cy in range(gh):
                    if (max_x, cy) not in k["visited"]:
                        return _move_toward(pos, (max_x, cy), min_x, max_x, gh)
                # All visited? scan again (disposal might have been missed)
                return _random_move(pos, min_x, max_x, gh, self.random)
            return _move_toward(pos, (max_x, pos[1]), min_x, max_x, gh)

        # 4. If standing on red waste, pick it up
        if pos in neighbors:
            cell_wastes = neighbors[pos].get("wastes", [])
            if "red" in cell_wastes:
                return {"type": "pick_up", "waste_type": "red"}

        # 5. Move toward nearest known red waste
        red_positions = [
            p for p, types in k["known_wastes"].items()
            if "red" in types
        ]
        if red_positions:
            nearest = min(red_positions, key=lambda p: abs(p[0] - pos[0]) + abs(p[1] - pos[1]))
            return _move_toward(pos, nearest, min_x, max_x, gh)

        # 6. Explore unvisited tiles
        target = _nearest_unvisited(pos, k["visited"], min_x, max_x, gh)
        if target:
            return _move_toward(pos, target, min_x, max_x, gh)

        # 7. Random move
        return _random_move(pos, min_x, max_x, gh, self.random)
