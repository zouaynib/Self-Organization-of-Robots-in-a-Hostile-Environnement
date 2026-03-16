# Group: [Your Group Number]
# Date: 2026-03-16
# Members: [Names]

import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from model import RobotMission
from objects import Radioactivity, Waste, WasteDisposal
from agents import GreenAgent, YellowAgent, RedAgent


def agent_portrayal(agent):
    """Only render robots via Mesa's scatter. Waste drawn in post_process."""
    if isinstance(agent, (GreenAgent, YellowAgent, RedAgent)):
        colors = {GreenAgent: "#2e7d32", YellowAgent: "#e65100", RedAgent: "#b71c1c"}
        return {"color": colors[type(agent)], "marker": "o", "size": 350, "zorder": 5}
    return {"size": 0, "color": "none"}


def post_process(ax):
    x_max = ax.get_xlim()[1]
    y_max = ax.get_ylim()[1]
    width = round(x_max)
    height = round(y_max)
    zone_w = width / 3

    # ── Zone backgrounds ──
    zone_colors = [("#e8f5e9", "Z1\n(low)"), ("#fff8e1", "Z2\n(med)"), ("#ffebee", "Z3\n(high)")]
    for i, (color, label) in enumerate(zone_colors):
        rect = mpatches.FancyBboxPatch(
            (i * zone_w - 0.5, -0.5), zone_w, y_max,
            boxstyle="square,pad=0", facecolor=color,
            edgecolor="#bdbdbd", linewidth=1.2, zorder=0
        )
        ax.add_patch(rect)
        ax.text(i * zone_w + zone_w / 2 - 0.5, height - 0.4, label,
                fontsize=9, ha="center", va="top", fontweight="bold",
                color="#9e9e9e", fontstyle="italic")

    # ── Disposal zone ──
    dx, dy = model.disposal_pos
    disp_rect = mpatches.FancyBboxPatch(
        (dx - 0.45, dy - 0.45), 0.9, 0.9,
        boxstyle="round,pad=0.05", facecolor="#263238",
        edgecolor="white", linewidth=2, zorder=1
    )
    ax.add_patch(disp_rect)
    ax.text(dx, dy, "🗑", fontsize=13, ha="center", va="center", zorder=2)

    # ── Draw waste as colored rounded squares ──
    waste_face = {"green": "#81c784", "yellow": "#ffd54f", "red": "#e57373"}
    waste_edge = {"green": "#388e3c", "yellow": "#f9a825", "red": "#c62828"}
    waste_label = {"green": "G", "yellow": "Y", "red": "R"}
    for agent in model.agents:
        if isinstance(agent, Waste) and agent.pos is not None:
            x, y = agent.pos
            rect = mpatches.FancyBboxPatch(
                (x - 0.3, y - 0.3), 0.6, 0.6,
                boxstyle="round,pad=0.06",
                facecolor=waste_face[agent.waste_type],
                edgecolor=waste_edge[agent.waste_type],
                linewidth=1.5, zorder=3
            )
            ax.add_patch(rect)
            ax.text(x, y, waste_label[agent.waste_type],
                    fontsize=7, ha="center", va="center",
                    fontweight="bold", color=waste_edge[agent.waste_type], zorder=4)

    # ── Show robot inventory (small dots near the robot) ──
    inv_colors = {"green": "#81c784", "yellow": "#ffd54f", "red": "#e57373"}
    for agent in model.agents:
        if isinstance(agent, (GreenAgent, YellowAgent, RedAgent)) and agent.pos:
            inv = agent.knowledge["inventory"]
            if inv:
                for i, w_type in enumerate(inv):
                    offset_x = -0.25 + i * 0.25
                    ax.plot(agent.pos[0] + offset_x, agent.pos[1] + 0.35,
                            "s", color=inv_colors.get(w_type, "gray"),
                            markersize=5, markeredgecolor="white",
                            markeredgewidth=0.5, zorder=6)

    # ── Title: stored waste count ──
    stored = model.stored_waste
    total = model._init_waste_count // 4
    ax.set_title(f"♻ Stored: {stored} / {total}   |   Step: {model.steps}",
                 fontsize=13, fontweight="bold", pad=10)

    # ── Legend: transformation pipeline ──
    legend_elements = [
        mlines.Line2D([], [], color="#2e7d32", marker="o", linestyle="None",
                       markersize=10, label="Green Robot"),
        mlines.Line2D([], [], color="#e65100", marker="o", linestyle="None",
                       markersize=10, label="Yellow Robot"),
        mlines.Line2D([], [], color="#b71c1c", marker="o", linestyle="None",
                       markersize=10, label="Red Robot"),
        mpatches.Patch(facecolor="#81c784", edgecolor="#388e3c", label="Green Waste"),
        mpatches.Patch(facecolor="#ffd54f", edgecolor="#f9a825", label="Yellow Waste"),
        mpatches.Patch(facecolor="#e57373", edgecolor="#c62828", label="Red Waste"),
        mpatches.Patch(facecolor="#263238", edgecolor="white", label="Disposal Zone"),
    ]
    ax.legend(handles=legend_elements, loc="upper left",
              fontsize=7, framealpha=0.9, ncol=2,
              bbox_to_anchor=(-0.02, -0.06))

    # ── Pipeline text below legend ──
    ax.text(0.5, -0.14,
            "Pipeline:  2×🟢 → 1×🟡 → 2×🟡 → 1×🔴 → 🗑 Disposal",
            transform=ax.transAxes, fontsize=9, ha="center",
            color="#424242", fontstyle="italic",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                      edgecolor="#bdbdbd", alpha=0.9))


space_component = make_space_component(agent_portrayal, post_process=post_process)
waste_chart = make_plot_component(
    {"Green Waste": "green", "Yellow Waste": "gold", "Red Waste": "red", "Stored Waste": "black"}
)


model = RobotMission()

page = SolaraViz(
    model,
    components=[space_component, waste_chart],
    name="Robot Mission",
)
