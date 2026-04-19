import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from src.model import RobotMission
from src.objects import Waste, Wall, DisposalZone
from src.agents import Robot

# --- Simulation ---
model = RobotMission(seed=42)
for _ in range(500):
    model.step()
    if sum(model.waste_counts[k] for k in ("green","yellow","red")) == 0:
        break

# --- Plot 1 : métriques ---
df = model.datacollector.get_model_vars_dataframe()
fig, ax = plt.subplots(figsize=(10, 4))
df[["Green Waste","Yellow Waste","Red Waste","Disposed"]].plot(ax=ax,
    color=["#4caf50","#fdd835","#e53935","#1565c0"])
ax.set_title("Waste over time")
ax.set_xlabel("Step")
ax.set_ylabel("Count")
plt.tight_layout()
plt.savefig("metrics.png", dpi=150)
plt.show()

# --- Plot 2 : état final de la grille ---
W, H = model.width, model.height
fig2, ax2 = plt.subplots(figsize=(10, 10))

z1 = plt.Rectangle((0,0), model.z1_max, H, color="#b7e4c7", alpha=0.4)
z2 = plt.Rectangle((model.z1_max,0), model.z2_max-model.z1_max, H, color="#ffe8a1", alpha=0.4)
z3 = plt.Rectangle((model.z2_max,0), W-model.z2_max, H, color="#ffb3b3", alpha=0.4)
for p in [z1,z2,z3]: ax2.add_patch(p)

for agents, (x, y) in model.grid.coord_iter():
    for agent in agents:
        if isinstance(agent, Wall):
            ax2.add_patch(plt.Rectangle((x,y),1,1,color="#555"))
        elif isinstance(agent, DisposalZone):
            ax2.plot(x+0.5, y+0.5, "*", color="gold", markersize=14)
        elif isinstance(agent, Waste):
            c = {"green":"#4caf50","yellow":"#fdd835","red":"#e53935"}[agent.waste_type]
            ax2.plot(x+0.5, y+0.5, "o", color=c, markersize=8)
        elif isinstance(agent, Robot):
            m2 = {"green":"^","yellow":"s","red":"D"}[agent.robot_type]
            c  = {"green":"#1b5e20","yellow":"#f57f17","red":"#b71c1c"}[agent.robot_type]
            ax2.plot(x+0.5, y+0.5, m2, color=c, markersize=10)

ax2.set_xlim(0,W); ax2.set_ylim(0,H)
ax2.grid(True, linewidth=0.3, alpha=0.4)
ax2.set_title("Final grid state")
plt.tight_layout()
plt.savefig("grid.png", dpi=150)
plt.show()

print("Done. Saved: metrics.png, grid.png")