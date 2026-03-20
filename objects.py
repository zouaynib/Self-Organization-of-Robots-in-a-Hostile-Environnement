# =============================================================================
# objects.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================
# Passive environment objects: Waste, Wall, DisposalZone, Radioactivity

import mesa


class Radioactivity(mesa.Agent):
    """
    Passive agent that encodes the radioactivity level of a cell.
    - Zone z1 (x in [0, W/3))      → level in [0.00, 0.33)
    - Zone z2 (x in [W/3, 2W/3))   → level in [0.33, 0.66)
    - Zone z3 (x in [2W/3, W))     → level in [0.66, 1.00]
    Robots read this to know which zone they are in.
    """

    def __init__(self, model, zone: int):
        super().__init__(model)
        self.zone = zone  # 1, 2, or 3

        if zone == 1:
            self.level = model.random.uniform(0.0, 0.33)
        elif zone == 2:
            self.level = model.random.uniform(0.33, 0.66)
        else:
            self.level = model.random.uniform(0.66, 1.0)

    def step(self):
        pass  # No behaviour


class Waste(mesa.Agent):
    """
    Waste object.  waste_type ∈ {"green", "yellow", "red"}
    """

    def __init__(self, model, waste_type: str):
        super().__init__(model)
        self.waste_type = waste_type

    def step(self):
        pass  # No behaviour


class Wall(mesa.Agent):
    """
    Impassable wall cell.
    """

    def __init__(self, model):
        super().__init__(model)

    def step(self):
        pass  # No behaviour


class DisposalZone(mesa.Agent):
    """
    Final waste disposal zone — placed in z3 (eastern column).
    Red robots deposit red waste here to complete the mission.
    """

    def __init__(self, model):
        super().__init__(model)

    def step(self):
        pass  # No behaviour