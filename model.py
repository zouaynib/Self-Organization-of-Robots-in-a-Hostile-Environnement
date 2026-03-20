# =============================================================================
# model.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================
#
# Zone access — enforced here in do() MOVE validation (mirrors agents.py):
#   GREEN  robot: tx must be < W//3              (z1 only)
#   YELLOW robot: tx must be < 2*W//3            (z1 + z2)
#   RED    robot: no restriction                  (z1 + z2 + z3)
#
# Exception: a robot carrying its product waste for hand-off may step
# exactly 1 column past its normal limit (relaxed=True).

import mesa
from agents import Robot, MOVE, PICK, TRANSFORM, DROP, WAIT
from objects  import Waste, Wall, DisposalZone, Radioactivity
from communication import CommunicationSystem


class RobotMission(mesa.Model):

    def __init__(
        self,
        width=30, height=30,
        n_green_robots=3, n_yellow_robots=3, n_red_robots=3,
        n_green_waste=20, n_yellow_waste=10, n_red_waste=5,
        n_walls=40,
        communication=True,
    ):
        super().__init__()
        self.width  = width
        self.height = height
        self.communication = communication
        self.communication_system = CommunicationSystem() if communication else None
        self.grid = mesa.space.MultiGrid(width, height, torus=False)
        self.waste_counts = {"green": 0, "yellow": 0, "red": 0, "disposed": 0}

        # 1. Radioactivity layer
        for x in range(width):
            for y in range(height):
                zone = 1 if x < width//3 else (2 if x < 2*width//3 else 3)
                self.grid.place_agent(Radioactivity(self, zone), (x, y))

        # 2. Walls (never on zone-boundary columns)
        wall_positions = set()
        att = 0
        while len(wall_positions) < n_walls and att < n_walls * 20:
            x = self.random.randrange(width)
            y = self.random.randrange(height)
            if x not in (width//3, 2*width//3):
                wall_positions.add((x, y))
            att += 1
        for wp in wall_positions:
            self.grid.place_agent(Wall(self), wp)
        self._wall_positions = wall_positions

        # 3. Waste — placed in correct zones
        #    green  -> z1  x in [0,       W//3-1]
        #    yellow -> z2  x in [W//3,   2W//3-1]
        #    red    -> z3  x in [2W//3,    W-2]   (col W-1 reserved for disposal)
        for wtype, count, x0, x1 in [
            ("green",  n_green_waste,  0,          width//3 - 1),
            ("yellow", n_yellow_waste, width//3,   2*width//3 - 1),
            ("red",    n_red_waste,    2*width//3, width - 2),
        ]:
            for _ in range(count):
                pos = self._free_pos(x0, x1, 0, height-1)
                self.grid.place_agent(Waste(self, wtype), pos)
                self.waste_counts[wtype] += 1

        # 4. Disposal zone — rightmost column (x = W-1)
        dy = self.random.randrange(height)
        while (width-1, dy) in self._wall_positions:
            dy = self.random.randrange(height)
        self._disposal_pos = (width-1, dy)
        self.grid.place_agent(DisposalZone(self), self._disposal_pos)

        # 5. Robots — each type starts in its home zone
        #    green  starts in z1  x in [0,       W//3-1]
        #    yellow starts in z2  x in [W//3,   2W//3-1]
        #    red    starts in z3  x in [2W//3,    W-1  ]
        for rtype, count, x0, x1 in [
            ("green",  n_green_robots,  0,          width//3 - 1),
            ("yellow", n_yellow_robots, width//3,   2*width//3 - 1),
            ("red",    n_red_robots,    2*width//3, width - 1),
        ]:
            for _ in range(count):
                pos = self._free_pos(x0, x1, 0, height-1)
                self.grid.place_agent(Robot(self, rtype), pos)

        # 6. Index for targeted messaging
        self.robots_by_type: dict[str, list[int]] = {
            "green": [], "yellow": [], "red": []
        }
        for agent in self.agents:
            if isinstance(agent, Robot):
                self.robots_by_type[agent.robot_type].append(agent.unique_id)

        # 7. Pre-fill disposal_pos in all red robots
        #    -> they know their target from step 1, no exploration needed
        for agent in self.agents:
            if isinstance(agent, Robot) and agent.robot_type == "red":
                agent.knowledge["disposal_pos"] = self._disposal_pos

        # 8. DataCollector
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Green Waste":  lambda m: m.waste_counts["green"],
                "Yellow Waste": lambda m: m.waste_counts["yellow"],
                "Red Waste":    lambda m: m.waste_counts["red"],
                "Disposed":     lambda m: m.waste_counts["disposed"],
                "Total Waste":  lambda m: sum(
                    v for k, v in m.waste_counts.items() if k != "disposed"
                ),
            }
        )

    # =========================================================================
    # Helpers
    # =========================================================================

    def _free_pos(self, x0, x1, y0, y1, tries=300):
        for _ in range(tries):
            x = self.random.randint(x0, x1)
            y = self.random.randint(y0, y1)
            if (x, y) not in self._wall_positions:
                return (x, y)
        for x in range(x0, x1+1):
            for y in range(y0, y1+1):
                if (x, y) not in self._wall_positions:
                    return (x, y)
        raise RuntimeError(f"No free cell in [{x0},{x1}]x[{y0},{y1}]")

    def _percepts(self, pos) -> dict:
        cells = self.grid.get_neighborhood(pos, moore=True, include_center=True, radius=1)
        return {c: self.grid.get_cell_list_contents(c) for c in cells}

    # =========================================================================
    # do() — validate and execute agent actions
    # =========================================================================

    def do(self, agent: Robot, action: dict) -> dict:
        atype = action.get("type", WAIT)
        pos   = agent.pos

        # ------------------------------------------------------------------ #
        # MOVE
        # Enforces zone constraints IDENTICALLY to agents._walkable()
        # ------------------------------------------------------------------ #
        if atype == MOVE:
            target = action.get("target")
            if target is None:
                return self._percepts(pos)

            tx, ty = target

            # Grid bounds
            if not (0 <= tx < self.width and 0 <= ty < self.height):
                return self._percepts(pos)

            # Adjacency (Moore)
            if abs(tx - pos[0]) > 1 or abs(ty - pos[1]) > 1:
                return self._percepts(pos)

            # Zone constraint — must match _walkable() in agents.py exactly
            # relaxed=True only when carrying transformed product for hand-off
            relaxed = (
                agent._product_waste is not None
                and agent._product_waste in agent.knowledge["inventory"]
            )
            extra = 1 if relaxed else 0

            if agent.robot_type == "green"  and tx >= self.width  // 3   + extra:
                return self._percepts(pos)   # GREEN cannot enter z2 (or beyond)

            if agent.robot_type == "yellow" and tx >= 2*self.width // 3  + extra:
                return self._percepts(pos)   # YELLOW cannot enter z3 (or beyond)

            # RED: no x restriction — can move anywhere

            # Wall check
            if any(isinstance(o, Wall)
                   for o in self.grid.get_cell_list_contents((tx, ty))):
                return self._percepts(pos)

            self.grid.move_agent(agent, (tx, ty))

        # ------------------------------------------------------------------ #
        # PICK
        # ------------------------------------------------------------------ #
        elif atype == PICK:
            if len(agent.knowledge["inventory"]) >= Robot.CAPACITY:
                return self._percepts(agent.pos)

            cell = self.grid.get_cell_list_contents(agent.pos)
            waste_obj = next(
                (o for o in cell
                 if isinstance(o, Waste) and o.waste_type == agent._target_waste),
                None,
            )
            if waste_obj is None:
                return self._percepts(agent.pos)

            self.grid.remove_agent(waste_obj)
            if hasattr(waste_obj, "remove"):
                waste_obj.remove()

            agent.knowledge["inventory"].append(waste_obj.waste_type)
            agent.knowledge["known_waste"].pop(agent.pos, None)
            self.waste_counts[waste_obj.waste_type] = max(
                0, self.waste_counts[waste_obj.waste_type] - 1
            )
            agent._notify_collected(agent.pos)

        # ------------------------------------------------------------------ #
        # TRANSFORM
        #   green:  2×green  -> 1×yellow  (stays in inventory)
        #   yellow: 2×yellow -> 1×red     (stays in inventory)
        # ------------------------------------------------------------------ #
        elif atype == TRANSFORM:
            inv    = agent.knowledge["inventory"]
            target = agent._target_waste
            prod   = agent._product_waste
            needed = agent._transform_count

            if needed == 0 or inv.count(target) < needed or prod is None:
                return self._percepts(agent.pos)

            for _ in range(needed):
                inv.remove(target)
            inv.append(prod)

            self.waste_counts[prod] = self.waste_counts.get(prod, 0) + 1

        # ------------------------------------------------------------------ #
        # DROP
        #   red @ DisposalZone -> permanently disposed
        #   otherwise          -> placed on grid for next robot type
        # ------------------------------------------------------------------ #
        elif atype == DROP:
            inv = agent.knowledge["inventory"]
            if not inv:
                return self._percepts(agent.pos)

            waste_type  = inv[-1]
            cell        = self.grid.get_cell_list_contents(agent.pos)
            at_disposal = any(isinstance(o, DisposalZone) for o in cell)

            if agent.robot_type == "red" and at_disposal:
                inv.pop()
                self.waste_counts["red"]      = max(0, self.waste_counts["red"] - 1)
                self.waste_counts["disposed"] += 1
            else:
                new_waste = Waste(self, waste_type)
                self.grid.place_agent(new_waste, agent.pos)
                inv.pop()
                # Notify responsible robots that new waste appeared here
                agent._notify_responsible(agent.pos, waste_type)

        return self._percepts(agent.pos)

    # =========================================================================
    # Model step
    # =========================================================================

    def step(self):
        self.datacollector.collect(self)
        self.agents.shuffle_do("step")
        if self.communication and self.communication_system:
            self.communication_system.clear_broadcasts()