# =============================================================================
# server.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================
# Solara/Mesa visualization: colored zone backgrounds, clear agent rendering,
# live legend, and waste-over-time chart.

import solara
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd

from mesa.visualization import SolaraViz, make_space_component, make_plot_component

from model import RobotMission
from agents import Robot
from objects import Waste, Wall, DisposalZone, Radioactivity


# =============================================================================
# Agent portrayal
# =============================================================================

def agent_portrayal(agent):
    """Return a Mesa portrayal dict for each agent type."""

    # ------------------------------------------------------------------
    # Robots — large markers with distinct colors
    # ------------------------------------------------------------------
    if isinstance(agent, Robot):
        color_map = {
            "green":  "#1a9641",   # deep green
            "yellow": "#d9a520",   # amber
            "red":    "#d73027",   # vivid red
        }
        marker_map = {
            "green":  "^",   # triangle up
            "yellow": "s",   # square
            "red":    "D",   # diamond
        }
        return {
            "color":  color_map[agent.robot_type],
            "size":   220,
            "marker": marker_map[agent.robot_type],
            "zorder": 4,
        }

    # ------------------------------------------------------------------
    # Waste — medium circles
    # ------------------------------------------------------------------
    if isinstance(agent, Waste):
        color_map = {
            "green":  "#52b788",
            "yellow": "#f4a261",
            "red":    "#e63946",
        }
        return {
            "color":  color_map.get(agent.waste_type, "grey"),
            "size":   90,
            "marker": "o",
            "zorder": 3,
        }

    # ------------------------------------------------------------------
    # Disposal zone — blue star
    # ------------------------------------------------------------------
    if isinstance(agent, DisposalZone):
        return {
            "color":  "#023e8a",
            "size":   350,
            "marker": "*",
            "zorder": 3,
        }

    # ------------------------------------------------------------------
    # Walls — dark squares
    # ------------------------------------------------------------------
    if isinstance(agent, Wall):
        return {
            "color":  "#2d2d2d",
            "size":   180,
            "marker": "s",
            "zorder": 2,
        }

    # Radioactivity — invisible
    return {"color": "none", "size": 0}


# =============================================================================
# Zone background overlay
# =============================================================================

def zones_background(ax):
    """Draw semi-transparent colored rectangles for z1 / z2 / z3."""
    W = 30
    H = 30

    zone_style = [
        # (x_origin, width, face_color,  label)
        (0,       W/3, "#b7e4c7", "z1 – Low radioactivity"),
        (W/3,     W/3, "#ffe8a1", "z2 – Medium radioactivity"),
        (2*W/3,   W/3, "#ffb3b3", "z3 – High radioactivity"),
    ]

    for x0, w, fc, _ in zone_style:
        rect = mpatches.Rectangle(
            (x0 - 0.5, -0.5),  # offset to align with cell centres
            w, H,
            facecolor=fc,
            alpha=0.35,
            linewidth=0,
            zorder=0,
        )
        ax.add_patch(rect)

    # Zone boundary lines
    for bx in (W/3, 2*W/3):
        ax.axvline(x=bx - 0.5, color="#888888", linewidth=1.0,
                   linestyle="--", zorder=1, alpha=0.6)

    ax.set_xlim(-0.5, W - 0.5)
    ax.set_ylim(-0.5, H - 0.5)


# =============================================================================
# Solara components
# =============================================================================

def make_legend(_model):
    """Render a Markdown legend panel."""
    return solara.Markdown(
        """
### Robots
| Symbol | Type | Zone |
|--------|------|------|
| 🔺 Green robot | Collects green waste → yellow | z1 only |
| 🟥 Yellow robot | Collects yellow waste → red | z1–z2 |
| 🔷 Red robot | Transports red waste to disposal | z1–z3 |

### Waste & Objects
| Symbol | Meaning |
|--------|---------|
| 🟢 Green circle | Green waste (z1) |
| 🟡 Yellow circle | Yellow waste |
| 🔴 Red circle | Red waste |
| ⭐ Blue star | Disposal zone |
| ⬛ Dark square | Wall |

### Zone colours
🟩 z1 – Low radioactivity &nbsp; 🟨 z2 – Medium &nbsp; 🟥 z3 – High
        """
    )


# =============================================================================
# Model instantiation
# =============================================================================

model_params = {
    "communication": {
        "type": "Select",
        "value": True,
        "values": [True, False],
        "label": "Agent communication",
    },
    "n_green_waste": {
        "type": "SliderInt",
        "value": 20,
        "min": 5,
        "max": 50,
        "step": 5,
        "label": "Initial green waste (z1)",
    },
    "n_yellow_waste": {
        "type": "SliderInt",
        "value": 10,
        "min": 0,
        "max": 30,
        "step": 5,
        "label": "Initial yellow waste (z2)",
    },
    "n_red_waste": {
        "type": "SliderInt",
        "value": 5,
        "min": 0,
        "max": 20,
        "step": 1,
        "label": "Initial red waste (z3)",
    },
    "n_walls": {
        "type": "SliderInt",
        "value": 40,
        "min": 0,
        "max": 80,
        "step": 5,
        "label": "Number of walls",
    },
    "n_green_robots": {
        "type": "SliderInt",
        "value": 3,
        "min": 1,
        "max": 6,
        "step": 1,
        "label": "Green robots (z1)",
    },
    "n_yellow_robots": {
        "type": "SliderInt",
        "value": 3,
        "min": 1,
        "max": 6,
        "step": 1,
        "label": "Yellow robots (z1+z2)",
    },
    "n_red_robots": {
        "type": "SliderInt",
        "value": 3,
        "min": 1,
        "max": 6,
        "step": 1,
        "label": "Red robots (z1+z2+z3)",
    },
}

model = RobotMission()

SpaceGraph = make_space_component(
    agent_portrayal,
    post_process=zones_background,
)

WastePlot = make_plot_component(
    {
        "Green Waste":  "#52b788",
        "Yellow Waste": "#f4a261",
        "Red Waste":    "#e63946",
        "Disposed":     "#023e8a",
    }
)

# =============================================================================
# Page
# =============================================================================

page = SolaraViz(
    model,
    components=[make_legend, SpaceGraph, WastePlot],
    model_params=model_params,
    name="Self-Organization of Robots in a Hostile Environment",
)

page