# Group: [Your Group Number]
# Date: 2026-03-16
# Members: [Names]

from mesa import Agent


class Radioactivity(Agent):
    """Non-behaving agent representing radioactivity on a cell.
    Allows robots to detect which zone they are in."""

    def __init__(self, model, zone):
        super().__init__(model)
        self.zone = zone
        if zone == 1:
            self.level = self.random.uniform(0, 0.33)
        elif zone == 2:
            self.level = self.random.uniform(0.33, 0.66)
        else:
            self.level = self.random.uniform(0.66, 1.0)


class Waste(Agent):
    """Non-behaving agent representing a waste object."""

    def __init__(self, model, waste_type):
        super().__init__(model)
        self.waste_type = waste_type  # "green", "yellow", "red"


class WasteDisposal(Agent):
    """Non-behaving agent marking the waste disposal cell (east edge of z3)."""

    def __init__(self, model):
        super().__init__(model)
