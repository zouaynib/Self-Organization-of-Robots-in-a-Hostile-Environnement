# =============================================================================
# agents.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================
#
# Zone access rules (enforced in both _walkable AND model.do):
#
#   GREEN  robot  -> z1 ONLY        x in [0,     W/3)
#   YELLOW robot  -> z1 + z2        x in [0,  2*W/3)
#   RED    robot  -> z1 + z2 + z3   x in [0,     W)
#
# The only exception is a 1-column relaxation during hand-off DROP:
#   - green  carrying yellow: may step into x = W/3   (first col of z2) to drop
#   - yellow carrying red:    may step into x = 2*W/3 (first col of z3) to drop
#   After dropping, the robot immediately moves back into its normal zone.

from collections import deque
import mesa
from src.objects import Waste, Wall, DisposalZone
from src.communication import Message

MOVE      = "MOVE"
PICK      = "PICK"
TRANSFORM = "TRANSFORM"
DROP      = "DROP"
WAIT      = "WAIT"


class Robot(mesa.Agent):

    CAPACITY = 2

    def __init__(self, model, robot_type: str):
        super().__init__(model)
        self.robot_type = robot_type
        w = model.width

        # --- Zone x-limits (strict upper bound, inclusive) ---
        # green  : x <= W//3 - 1         (z1 only)
        # yellow : x <= 2*W//3 - 1       (z1 + z2)
        # red    : x <= W - 1            (all zones)
        self._zone_max_x = {
            "green":  w // 3 - 1,
            "yellow": 2 * w // 3 - 1,
            "red":    w - 1,
        }[robot_type]

        
        self._target_waste    = robot_type   # what this robot collects
        self._product_waste   = {"green": "yellow", "yellow": "red",  "red": None}[robot_type]
        self._transform_count = {"green": 2,         "yellow": 2,     "red": 0   }[robot_type]

        # x-column where the transformed product must be dropped
        # (= first column of the NEXT zone, just beyond normal zone limit)
        self._drop_x = {"green": w // 3, "yellow": 2 * w // 3, "red": None}[robot_type]

        self.knowledge = {
            "pos":          None,
            "inventory":    [],
            "carrying":     0,
            "percepts":     {},
            "known_waste":  {},    
            "disposal_pos": None,  
            "last_action":  WAIT,
            "steps_idle":   0,
        }

    # =========================================================================
  
    def step(self):
        percepts     = self._perceive()
        self._update_knowledge(percepts)
        action       = self._deliberate(self.knowledge)
        new_percepts = self.model.do(self, action)
        self._update_knowledge(new_percepts)
        self.knowledge["last_action"] = action["type"]

   

    def _perceive(self) -> dict:
        if self.pos is None:
            return {}
        cells = self.model.grid.get_neighborhood(
            self.pos, moore=True, include_center=True, radius=1
        )
        return {c: self.model.grid.get_cell_list_contents(c) for c in cells}


    def _update_knowledge(self, percepts: dict):
        k             = self.knowledge
        k["pos"]      = self.pos
        k["percepts"] = percepts
        k["carrying"] = len(k["inventory"])

        for cell_pos, contents in percepts.items():
            for obj in contents:
                if isinstance(obj, Waste):
                    wtype = obj.waste_type
                    if k["known_waste"].get(cell_pos) != wtype:
                        k["known_waste"][cell_pos] = wtype
                        if wtype != self._target_waste:
                            self._notify_responsible(cell_pos, wtype)
                elif isinstance(obj, DisposalZone):
                    if k["disposal_pos"] != cell_pos:
                        k["disposal_pos"] = cell_pos
                        self._notify_disposal(cell_pos)

        if self.model.communication and self.model.communication_system:
            for msg in self.model.communication_system.get_messages(self.unique_id):
                if msg.performative == "INFORM_WASTE":
                    p = tuple(msg.content.get("pos", (-1,-1)))
                    w = msg.content.get("waste_type")
                    if w and p != (-1,-1) and p not in k["known_waste"]:
                        k["known_waste"][p] = w
                elif msg.performative == "INFORM_COLLECTED":
                    p = tuple(msg.content.get("pos", (-1,-1)))
                    k["known_waste"].pop(p, None)
                elif msg.performative == "DISPOSAL_POS":
                    if k["disposal_pos"] is None:
                        k["disposal_pos"] = tuple(msg.content.get("pos"))

        stale = [
            p for p in list(k["known_waste"])
            if not any(isinstance(o, Waste)
                       for o in self.model.grid.get_cell_list_contents(p))
        ]
        for p in stale:
            del k["known_waste"][p]


    def _deliberate(self, k: dict) -> dict:
        """
        Priority:
          1. TRANSFORM  — inventory full of target waste
          2. DELIVER    — red robot + red in inv -> BFS to DisposalZone -> DROP
          3. HAND-OFF   — green/yellow + product in inv -> BFS to drop_x -> DROP
          4. PICK       — target waste on current cell
          5. NAVIGATE   — BFS to nearest known target waste (within own zone)
          6. EXPLORE    — random walk (strictly within own zone, no relaxation)
        """
        pos       = k["pos"]
        inventory = k["inventory"]
        carrying  = k["carrying"]

        if pos is None:
            return {"type": WAIT}

        if (self._transform_count > 0
                and inventory.count(self._target_waste) >= self._transform_count):
            return {"type": TRANSFORM}

        
        if self.robot_type == "red" and "red" in inventory:
            disposal = k["disposal_pos"]
            if disposal is None:
               
                return self._bfs_move((min(pos[0]+1, self._zone_max_x), pos[1]),
                                      k, relaxed=False)
            if pos == disposal:
                return {"type": DROP}
            return self._bfs_move(disposal, k, relaxed=False)

      
        if self._product_waste and self._product_waste in inventory:
            drop_x = self._drop_x
            if pos[0] >= drop_x:
                return {"type": DROP}
           
            return self._bfs_move((drop_x, pos[1]), k, relaxed=True)

        
        if carrying < self.CAPACITY:
            for obj in k["percepts"].get(pos, []):
                if isinstance(obj, Waste) and obj.waste_type == self._target_waste:
                    return {"type": PICK}

       
        if carrying < self.CAPACITY:
            target = self._nearest_waste(k)
            if target is not None:
                if pos == target:
                    return {"type": PICK}
              
                return self._bfs_move(target, k, relaxed=False)

       
        k["steps_idle"] += 1
        return self._random_move(k, relaxed=False)

  

    def _nearest_waste(self, k: dict):
        """Nearest known waste of target type strictly within own zone."""
        pos = k["pos"]
        candidates = [
            p for p, wt in k["known_waste"].items()
            if wt == self._target_waste and p[0] <= self._zone_max_x
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: abs(p[0]-pos[0]) + abs(p[1]-pos[1]))

    def _bfs_move(self, target: tuple, k: dict, relaxed: bool) -> dict:
        """
        BFS shortest-path from current pos to target.
        relaxed=True  : allows entering 1 extra column (for product hand-off only).
        relaxed=False : strictly enforces zone limit.
        Returns MOVE for first step, or random move if target unreachable.
        """
        pos = k["pos"]
        if pos == target:
            return {"type": WAIT}

        visited = {pos: None}
        queue   = deque([pos])
        found   = False

        while queue:
            cur = queue.popleft()
            if cur == target:
                found = True
                break
            cx, cy = cur
            for nx, ny in [(cx+dx, cy+dy)
                           for dx in (-1,0,1) for dy in (-1,0,1)
                           if (dx,dy) != (0,0)]:
                if (nx,ny) not in visited and self._walkable((nx,ny), relaxed):
                    visited[(nx,ny)] = cur
                    queue.append((nx,ny))

        if not found:
            return self._random_move(k, relaxed=False)  

        step = target
        while visited[step] != pos:
            step = visited[step]
        return {"type": MOVE, "target": step}

    def _random_move(self, k: dict, relaxed: bool) -> dict:
        """Random walkable neighbour — strictly within zone (relaxed always False here)."""
        pos = k["pos"]
        neighbours = [
            (pos[0]+dx, pos[1]+dy)
            for dx in (-1,0,1) for dy in (-1,0,1)
            if (dx,dy) != (0,0)
        ]
        walkable = [n for n in neighbours if self._walkable(n, relaxed=False)]
        if not walkable:
            return {"type": WAIT}
        return {"type": MOVE, "target": self.model.random.choice(walkable)}

    def _walkable(self, pos: tuple, relaxed: bool) -> bool:
        """
        Returns True iff this robot is allowed to move to pos.

        Zone enforcement:
            GREEN  robot: x must be < W/3
                          (with relaxed=True: x must be < W/3 + 1 = W/3)
            YELLOW robot: x must be < 2*W/3
                          (with relaxed=True: x must be < 2*W/3 + 1)
            RED    robot: no x restriction

        The +1 relaxation is ONLY granted when the robot is carrying its
        transformed product waste and needs to step into the next zone to drop it.
        Any other movement (exploration, navigation, delivery) uses relaxed=False.
        """
        x, y = pos
        w, h = self.model.width, self.model.height

        
        if x < 0 or y < 0 or x >= w or y >= h:
            return False

        
        extra = 1 if relaxed else 0
        if self.robot_type == "green"  and x >= w // 3     + extra:
            return False
        if self.robot_type == "yellow" and x >= 2 * w // 3 + extra:
            return False
       

        
        if any(isinstance(o, Wall)
               for o in self.model.grid.get_cell_list_contents((x, y))):
            return False

        return True

    # =========================================================================
    # Communication
    # =========================================================================

    _WASTE_TO_ROBOT = {"green": "green", "yellow": "yellow", "red": "red"}

    def _notify_responsible(self, waste_pos, waste_type: str):
        if not (self.model.communication and self.model.communication_system):
            return
        rtype = self._WASTE_TO_ROBOT.get(waste_type)
        if not rtype:
            return
        recipients = [uid for uid in self.model.robots_by_type.get(rtype, [])
                      if uid != self.unique_id]
        if recipients:
            self.model.communication_system.send_to_group(
                Message(self.unique_id, None, "INFORM_WASTE",
                        {"pos": list(waste_pos), "waste_type": waste_type}),
                agent_ids=recipients,
            )

    def _notify_collected(self, waste_pos):
        if not (self.model.communication and self.model.communication_system):
            return
        self.model.communication_system.broadcast(
            Message(self.unique_id, None, "INFORM_COLLECTED",
                    {"pos": list(waste_pos)})
        )

    def _notify_disposal(self, disposal_pos):
        if not (self.model.communication and self.model.communication_system):
            return
        recipients = [uid for uid in self.model.robots_by_type.get("red", [])
                      if uid != self.unique_id]
        if recipients:
            self.model.communication_system.send_to_group(
                Message(self.unique_id, None, "DISPOSAL_POS",
                        {"pos": list(disposal_pos)}),
                agent_ids=recipients,
            )