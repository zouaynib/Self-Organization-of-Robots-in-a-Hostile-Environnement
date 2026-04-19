# animate.py
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
from src.model import RobotMission
from src.objects import Waste, Wall, DisposalZone
from src.agents import Robot

# --- Paramètres ---
N_STEPS = 300
INTERVAL = 200  # ms entre chaque frame

# --- Run simulation et sauvegarder les états ---
print("Running simulation...")
model = RobotMission(seed=42)
frames = []

for step in range(N_STEPS):
    model.step()

    # Snapshot de l'état courant
    snapshot = {
        "step": step,
        "waste_counts": dict(model.waste_counts),
        "agents": []
    }
    for agents, (x, y) in model.grid.coord_iter():
        for agent in agents:
            if isinstance(agent, Wall):
                snapshot["agents"].append(("wall", x, y, None))
            elif isinstance(agent, DisposalZone):
                snapshot["agents"].append(("disposal", x, y, None))
            elif isinstance(agent, Waste):
                snapshot["agents"].append(("waste", x, y, agent.waste_type))
            elif isinstance(agent, Robot):
                snapshot["agents"].append(("robot", x, y, agent.robot_type))

    frames.append(snapshot)

    # Arrêt anticipé si tout est disposé
    if sum(model.waste_counts[k] for k in ("green","yellow","red")) == 0:
        print(f"All waste disposed at step {step}!")
        break

print(f"Collected {len(frames)} frames. Building animation...")

# --- Setup figure ---
W, H = model.width, model.height
fig, (ax_grid, ax_chart) = plt.subplots(1, 2, figsize=(16, 8),
                                          gridspec_kw={"width_ratios": [1, 1]})

# Couleurs
WASTE_COLORS  = {"green": "#4caf50", "yellow": "#fdd835", "red": "#e53935"}
ROBOT_COLORS  = {"green": "#1b5e20", "yellow": "#f57f17", "red": "#b71c1c"}
ROBOT_MARKERS = {"green": "^",       "yellow": "s",       "red": "D"}

# Historique pour le chart
history = {k: [] for k in ("Green Waste","Yellow Waste","Red Waste","Disposed")}
step_history = []

def draw_frame(i):
    snap = frames[i]
    ax_grid.cla()
    ax_chart.cla()

    # --- Zones background ---
    ax_grid.add_patch(plt.Rectangle((0,0), model.z1_max, H,
                                    color="#b7e4c7", alpha=0.35, zorder=0))
    ax_grid.add_patch(plt.Rectangle((model.z1_max,0),
                                    model.z2_max-model.z1_max, H,
                                    color="#ffe8a1", alpha=0.35, zorder=0))
    ax_grid.add_patch(plt.Rectangle((model.z2_max,0),
                                    W-model.z2_max, H,
                                    color="#ffb3b3", alpha=0.35, zorder=0))

    # --- Agents ---
    for kind, x, y, attr in snap["agents"]:
        if kind == "wall":
            ax_grid.add_patch(plt.Rectangle((x, y), 1, 1,
                                            color="#444", zorder=1))
        elif kind == "disposal":
            ax_grid.plot(x+0.5, y+0.5, "*", color="gold",
                         markersize=16, zorder=3)
        elif kind == "waste":
            ax_grid.plot(x+0.5, y+0.5, "o",
                         color=WASTE_COLORS[attr],
                         markersize=7, zorder=2)
        elif kind == "robot":
            ax_grid.plot(x+0.5, y+0.5,
                         ROBOT_MARKERS[attr],
                         color=ROBOT_COLORS[attr],
                         markersize=12, zorder=4,
                         markeredgecolor="white", markeredgewidth=0.8)

    # Grid lines
    ax_grid.set_xlim(0, W); ax_grid.set_ylim(0, H)
    ax_grid.set_xticks(range(0, W, 5))
    ax_grid.set_yticks(range(0, H, 5))
    ax_grid.tick_params(labelsize=7)
    ax_grid.grid(True, linewidth=0.3, alpha=0.4)

    # Zone labels
    ax_grid.text(model.z1_max/2, H-1, "Zone 1", ha="center",
                 fontsize=9, color="#2d6a4f", fontweight="bold")
    ax_grid.text((model.z1_max+model.z2_max)/2, H-1, "Zone 2", ha="center",
                 fontsize=9, color="#9a6700", fontweight="bold")
    ax_grid.text((model.z2_max+W)/2, H-1, "Zone 3", ha="center",
                 fontsize=9, color="#900", fontweight="bold")

    wc = snap["waste_counts"]
    ax_grid.set_title(
        f"Step {snap['step']}  |  Green:{wc['green']}  Yellow:{wc['yellow']}  Red:{wc['red']}  Disposed:{wc['disposed']}",
        fontsize=11
    )

    # Legend
    legend_elems = [
        mpatches.Patch(color="#4caf50", label="Green waste"),
        mpatches.Patch(color="#fdd835", label="Yellow waste"),
        mpatches.Patch(color="#e53935", label="Red waste"),
        plt.Line2D([0],[0], marker="^", color="#1b5e20",
                   linestyle="None", markersize=9, label="Green robot"),
        plt.Line2D([0],[0], marker="s", color="#f57f17",
                   linestyle="None", markersize=9, label="Yellow robot"),
        plt.Line2D([0],[0], marker="D", color="#b71c1c",
                   linestyle="None", markersize=9, label="Red robot"),
        plt.Line2D([0],[0], marker="*", color="gold",
                   linestyle="None", markersize=12, label="Disposal zone"),
    ]
    ax_grid.legend(handles=legend_elems, loc="lower right", fontsize=7)

    # --- Chart ---
    step_history.append(snap["step"])
    history["Green Waste"].append(wc["green"])
    history["Yellow Waste"].append(wc["yellow"])
    history["Red Waste"].append(wc["red"])
    history["Disposed"].append(wc["disposed"])

    ax_chart.plot(step_history, history["Green Waste"],
                  color="#4caf50", label="Green waste", linewidth=2)
    ax_chart.plot(step_history, history["Yellow Waste"],
                  color="#fdd835", label="Yellow waste", linewidth=2)
    ax_chart.plot(step_history, history["Red Waste"],
                  color="#e53935", label="Red waste", linewidth=2)
    ax_chart.plot(step_history, history["Disposed"],
                  color="#1565c0", label="Disposed", linewidth=2, linestyle="--")

    ax_chart.set_xlim(0, len(frames))
    ax_chart.set_ylim(0, max(
        max(history["Green Waste"] or [1]),
        max(history["Yellow Waste"] or [1]),
        max(history["Red Waste"] or [1]),
        max(history["Disposed"] or [1]),
    ) + 2)
    ax_chart.set_xlabel("Step", fontsize=10)
    ax_chart.set_ylabel("Count", fontsize=10)
    ax_chart.set_title("Waste counts over time", fontsize=11)
    ax_chart.legend(fontsize=9)
    ax_chart.grid(True, alpha=0.3)

    plt.tight_layout()


ani = animation.FuncAnimation(
    fig, draw_frame,
    frames=len(frames),
    interval=INTERVAL,
    repeat=False
)

# Sauvegarder en MP4 (nécessite ffmpeg) ou GIF
try:
    print("Saving animation as simulation.mp4 ...")
    ani.save("simulation.mp4", writer="ffmpeg", fps=5, dpi=120)
    print("Saved: simulation.mp4")
except Exception as e:
    print(f"ffmpeg not found ({e}), saving as GIF instead...")
    ani.save("simulation.gif", writer="pillow", fps=5, dpi=80)
    print("Saved: simulation.gif")

print("Opening interactive window...")
plt.show()
