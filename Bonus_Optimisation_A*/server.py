# Group: XX | Date: 2026-04-19 | Members: ...
"""server.py — Solara visualization."""

import solara
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.colors import ListedColormap

from src.model import RobotMission
from src.objects import Waste, Wall, DisposalZone, Radioactivity
from src.agents import Robot

# ---------------------------------------------------------------------------
# Reactive state
# ---------------------------------------------------------------------------
model_state = solara.reactive(None)

# Sliders
communication    = solara.reactive(True)
n_green_waste    = solara.reactive(20)
n_yellow_waste   = solara.reactive(10)
n_red_waste      = solara.reactive(5)
n_walls          = solara.reactive(40)
n_green_robots   = solara.reactive(3)
n_yellow_robots  = solara.reactive(3)
n_red_robots     = solara.reactive(3)
running          = solara.reactive(False)


def make_model():
    return RobotMission(
        n_green_robots=n_green_robots.value,
        n_yellow_robots=n_yellow_robots.value,
        n_red_robots=n_red_robots.value,
        n_green_waste=n_green_waste.value,
        n_yellow_waste=n_yellow_waste.value,
        n_red_waste=n_red_waste.value,
        n_walls=n_walls.value,
        communication=communication.value,
    )


def draw_grid(model):
    W, H = model.width, model.height
    fig, ax = plt.subplots(figsize=(10, 10))

    # Zone background
    z1 = plt.Rectangle((0, 0), model.z1_max, H,
                        color="#b7e4c7", alpha=0.4, zorder=0)
    z2 = plt.Rectangle((model.z1_max, 0), model.z2_max - model.z1_max, H,
                        color="#ffe8a1", alpha=0.4, zorder=0)
    z3 = plt.Rectangle((model.z2_max, 0), W - model.z2_max, H,
                        color="#ffb3b3", alpha=0.4, zorder=0)
    ax.add_patch(z1); ax.add_patch(z2); ax.add_patch(z3)

    for agents, (x, y) in model.grid.coord_iter():
        for agent in agents:
            if isinstance(agent, Wall):
                ax.add_patch(plt.Rectangle((x, y), 1, 1, color="#555", zorder=1))
            elif isinstance(agent, DisposalZone):
                ax.plot(x+0.5, y+0.5, "*", color="gold", markersize=14, zorder=3)
            elif isinstance(agent, Waste):
                color = {"green": "#4caf50", "yellow": "#fdd835", "red": "#e53935"}[agent.waste_type]
                ax.plot(x+0.5, y+0.5, "o", color=color, markersize=8, zorder=2)
            elif isinstance(agent, Robot):
                marker = {"green": "^", "yellow": "s", "red": "D"}[agent.robot_type]
                color  = {"green": "#1b5e20", "yellow": "#f57f17", "red": "#b71c1c"}[agent.robot_type]
                ax.plot(x+0.5, y+0.5, marker, color=color, markersize=10, zorder=4)

                # Draw vision radius
                rect = plt.Rectangle(
                    (x - 2 + 0.5, y - 2 + 0.5), 4, 4,
                    fill=False, edgecolor=color, linewidth=0.5,
                    linestyle="--", alpha=0.3, zorder=5
                )
                ax.add_patch(rect)

    ax.set_xlim(0, W); ax.set_ylim(0, H)
    ax.set_xticks(range(W)); ax.set_yticks(range(H))
    ax.tick_params(labelsize=6)
    ax.grid(True, linewidth=0.3, alpha=0.4)

    legend = [
        mpatches.Patch(color="#4caf50", label="Green waste"),
        mpatches.Patch(color="#fdd835", label="Yellow waste"),
        mpatches.Patch(color="#e53935", label="Red waste"),
        plt.Line2D([0],[0], marker="^", color="#1b5e20", linestyle="None", label="Green robot"),
        plt.Line2D([0],[0], marker="s", color="#f57f17", linestyle="None", label="Yellow robot"),
        plt.Line2D([0],[0], marker="D", color="#b71c1c", linestyle="None", label="Red robot"),
        plt.Line2D([0],[0], marker="*", color="gold",   linestyle="None", label="Disposal zone"),
    ]
    ax.legend(handles=legend, loc="upper right", fontsize=7)
    ax.set_title(
        f"Step {model.schedule.steps if hasattr(model,'schedule') else '?'} | "
        f"Disposed: {model.waste_counts['disposed']}",
        fontsize=11
    )
    plt.tight_layout()
    return fig


@solara.component
def Page():
    model = model_state.value

    with solara.Sidebar():
        solara.Markdown("## Configuration")
        solara.Checkbox(label="Communication", value=communication)
        solara.SliderInt("Green robots",  value=n_green_robots,  min=1, max=6)
        solara.SliderInt("Yellow robots", value=n_yellow_robots, min=1, max=6)
        solara.SliderInt("Red robots",    value=n_red_robots,    min=1, max=6)
        solara.SliderInt("Green waste",   value=n_green_waste,   min=5, max=50)
        solara.SliderInt("Yellow waste",  value=n_yellow_waste,  min=0, max=30)
        solara.SliderInt("Red waste",     value=n_red_waste,     min=0, max=20)
        solara.SliderInt("Walls",         value=n_walls,         min=0, max=80)

        def on_reset():
            model_state.set(make_model())
            running.set(False)

        solara.Button("Reset", on_click=on_reset, color="secondary")
        solara.Button(
            "▶ Run" if not running.value else "⏸ Pause",
            on_click=lambda: running.set(not running.value),
        )

    if model is None:
        model_state.set(make_model())
        return

    # Auto-step when running
    if running.value:
        model.step()
        model_state.set(model)

    solara.Markdown(
        f"**Green waste:** {model.waste_counts['green']} | "
        f"**Yellow waste:** {model.waste_counts['yellow']} | "
        f"**Red waste:** {model.waste_counts['red']} | "
        f"**Disposed:** {model.waste_counts['disposed']}"
    )

    fig = draw_grid(model)
    solara.FigureMatplotlib(fig)
    plt.close(fig)

    # Metrics chart
    df = model.datacollector.get_model_vars_dataframe()
    if len(df) > 1:
        fig2, ax2 = plt.subplots(figsize=(8, 3))
        df[["Green Waste","Yellow Waste","Red Waste","Disposed"]].plot(ax=ax2)
        ax2.set_xlabel("Step"); ax2.set_ylabel("Count")
        ax2.set_title("Waste over time")
        solara.FigureMatplotlib(fig2)
        plt.close(fig2)
