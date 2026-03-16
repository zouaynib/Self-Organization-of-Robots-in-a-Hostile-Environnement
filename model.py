# Group: [Your Group Number]
# Date: 2026-03-16
# Members: [Names]

from mesa import Model
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector

from objects import Radioactivity, Waste, WasteDisposal
from agents import GreenAgent, YellowAgent, RedAgent


class RobotMission(Model):
    """Model for the robot waste collection mission."""

    def __init__(
        self,
        width=12,
        height=12,
        n_green_waste=12,
        n_green_robots=3,
        n_yellow_robots=2,
        n_red_robots=1,
        seed=None,
    ):
        super().__init__(seed=seed)
        self.grid = MultiGrid(width, height, torus=False)
        self.stored_waste = 0  # count of wastes successfully disposed
        self._init_waste_count = n_green_waste

        # Zone boundaries (columns)
        zone_width = width // 3
        self.z1_max = zone_width - 1           # e.g. 0-3
        self.z2_max = 2 * zone_width - 1       # e.g. 4-7
        self.z3_max = width - 1                 # e.g. 8-11

        # --- Place radioactivity on every cell ---
        for x in range(width):
            for y in range(height):
                if x <= self.z1_max:
                    zone = 1
                elif x <= self.z2_max:
                    zone = 2
                else:
                    zone = 3
                r = Radioactivity(self, zone)
                self.grid.place_agent(r, (x, y))

        # --- Place waste disposal zone (random cell on east edge) ---
        disposal_y = self.random.randrange(height)
        self.disposal_pos = (self.z3_max, disposal_y)
        wd = WasteDisposal(self)
        self.grid.place_agent(wd, self.disposal_pos)

        # --- Place initial green waste randomly in z1 ---
        for _ in range(n_green_waste):
            x = self.random.randrange(0, self.z1_max + 1)
            y = self.random.randrange(height)
            w = Waste(self, "green")
            self.grid.place_agent(w, (x, y))

        # --- Create robots ---
        for _ in range(n_green_robots):
            agent = GreenAgent(self, max_x=self.z1_max)
            x = self.random.randrange(0, self.z1_max + 1)
            y = self.random.randrange(height)
            self.grid.place_agent(agent, (x, y))

        for _ in range(n_yellow_robots):
            agent = YellowAgent(self, max_x=self.z2_max)
            x = self.random.randrange(0, self.z2_max + 1)
            y = self.random.randrange(height)
            self.grid.place_agent(agent, (x, y))

        for _ in range(n_red_robots):
            agent = RedAgent(self, max_x=self.z3_max)
            x = self.random.randrange(0, self.z3_max + 1)
            y = self.random.randrange(height)
            self.grid.place_agent(agent, (x, y))

        # --- Data collector ---
        self.datacollector = DataCollector(
            model_reporters={
                "Green Waste": lambda m: self._count_waste(m, "green"),
                "Yellow Waste": lambda m: self._count_waste(m, "yellow"),
                "Red Waste": lambda m: self._count_waste(m, "red"),
                "Stored Waste": lambda m: m.stored_waste,
            }
        )

    # ------------------------------------------------------------------
    # Percepts: what the agent can see (current cell + Moore neighbors)
    # ------------------------------------------------------------------

    def get_percepts(self, agent):
        """Return percepts for the agent: contents of current + adjacent cells."""
        percepts = {}
        neighbors = self.grid.get_neighborhood(
            agent.pos, moore=True, include_center=True
        )
        for pos in neighbors:
            percepts[pos] = self._cell_contents(pos)
        return percepts

    def _cell_contents(self, pos):
        """Summarize what is at a given cell."""
        agents_here = self.grid.get_cell_list_contents([pos])
        wastes = [a.waste_type for a in agents_here if isinstance(a, Waste)]
        robots = [type(a).__name__ for a in agents_here if isinstance(a, (GreenAgent, YellowAgent, RedAgent))]
        disposal = any(isinstance(a, WasteDisposal) for a in agents_here)
        radio = [a for a in agents_here if isinstance(a, Radioactivity)]
        zone = radio[0].zone if radio else None
        return {
            "wastes": wastes,
            "robots": robots,
            "disposal": disposal,
            "zone": zone,
        }

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def do(self, agent, action):
        """Execute an action for the given agent. Returns new percepts."""
        action_type = action["type"]

        if action_type == "move":
            self._do_move(agent, action)
        elif action_type == "pick_up":
            self._do_pick_up(agent, action)
        elif action_type == "transform":
            self._do_transform(agent, action)
        elif action_type == "drop":
            self._do_drop(agent, action)
        # "wait" -> do nothing

        return self.get_percepts(agent)

    def _do_move(self, agent, action):
        dx = action.get("dx", 0)
        dy = action.get("dy", 0)
        new_x = agent.pos[0] + dx
        new_y = agent.pos[1] + dy

        # Bounds check
        if not (0 <= new_x < self.grid.width and 0 <= new_y < self.grid.height):
            return
        # Zone check
        if new_x < agent.min_x or new_x > agent.max_x:
            return

        self.grid.move_agent(agent, (new_x, new_y))

    def _do_pick_up(self, agent, action):
        waste_type = action.get("waste_type")
        agents_here = self.grid.get_cell_list_contents([agent.pos])
        for a in agents_here:
            if isinstance(a, Waste) and a.waste_type == waste_type:
                # Remove waste from grid and add to inventory
                self.grid.remove_agent(a)
                a.remove()
                agent.knowledge["inventory"].append(waste_type)
                return  # pick up one at a time

    def _do_transform(self, agent, action):
        from_type = action.get("from")
        to_type = action.get("to")
        inv = agent.knowledge["inventory"]

        # Green robot: 2 green -> 1 yellow
        # Yellow robot: 2 yellow -> 1 red
        count_needed = 2
        count_found = inv.count(from_type)
        if count_found >= count_needed:
            for _ in range(count_needed):
                inv.remove(from_type)
            inv.append(to_type)

    def _do_drop(self, agent, action):
        waste_type = action.get("waste_type")
        inv = agent.knowledge["inventory"]

        if waste_type not in inv:
            return

        inv.remove(waste_type)

        # If dropping red waste on disposal zone, it's stored
        if waste_type == "red" and agent.pos == self.disposal_pos:
            self.stored_waste += 1
        else:
            # Place waste on the grid for other robots to pick up
            w = Waste(self, waste_type)
            self.grid.place_agent(w, agent.pos)

    # ------------------------------------------------------------------
    # Model step
    # ------------------------------------------------------------------

    def step(self):
        self.datacollector.collect(self)

        # Check if mission is complete: no waste on grid and no waste in inventories
        waste_on_grid = any(isinstance(a, Waste) for a in self.agents)
        waste_in_inv = any(
            a.knowledge["inventory"]
            for a in self.agents
            if isinstance(a, (GreenAgent, YellowAgent, RedAgent))
        )
        if not waste_on_grid and not waste_in_inv and self.stored_waste > 0:
            self.running = False
            return

        # Shuffle and step only robot agents
        robots = [a for a in self.agents if isinstance(a, (GreenAgent, YellowAgent, RedAgent))]
        self.random.shuffle(robots)
        for robot in robots:
            robot.step()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_waste(model, waste_type):
        return sum(
            1 for a in model.agents
            if isinstance(a, Waste) and a.waste_type == waste_type
        )
