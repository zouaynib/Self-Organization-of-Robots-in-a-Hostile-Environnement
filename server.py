# =============================================================================
# server.py
# Self-organization of robots in a hostile environment
# CentraleSupélec MAS 2025-2026
# =============================================================================

import solara
import matplotlib.patches as mpatches

# --- Import compatible avec toutes les versions de Mesa ---
from mesa.visualization import SolaraViz, make_plot_component

try:
    from mesa.visualization import make_space_component
except ImportError:
    from mesa.visualization.components.matplotlib_components import make_space_component

from model import RobotMission
from agents import Robot
from objects import Waste, Wall, DisposalZone, Radioactivity


# =============================================================================
# Agent portrayal — compatible Mesa 3.x et 4.x
# =============================================================================

def agent_portrayal(agent):

    # Robots
    if isinstance(agent, Robot):
        colors  = {"green": "#1a9641", "yellow": "#d9a520", "red": "#d73027"}
        markers = {"green": "^",       "yellow": "s",       "red": "D"}
        return {
            "color":  colors[agent.robot_type],
            "size":   250,
            "marker": markers[agent.robot_type],
            "zorder": 4,
        }

    # Déchets
    if isinstance(agent, Waste):
        colors = {"green": "#52b788", "yellow": "#f4a261", "red": "#e63946"}
        return {
            "color":  colors.get(agent.waste_type, "grey"),
            "size":   100,
            "marker": "o",
            "zorder": 3,
        }

    # Zone de dépôt
    if isinstance(agent, DisposalZone):
        return {"color": "#023e8a", "size": 400, "marker": "*", "zorder": 3}

    # Murs
    if isinstance(agent, Wall):
        return {"color": "#2d2d2d", "size": 200, "marker": "s", "zorder": 2}

    # Radioactivité — invisible
    return {"color": "none", "size": 0, "marker": "."}


# =============================================================================
# Fond coloré par zone
# =============================================================================

def zones_background(ax):
    W, H = 30, 30
    zones = [
        (0,      W/3, "#b7e4c7"),
        (W/3,    W/3, "#ffe8a1"),
        (2*W/3,  W/3, "#ffb3b3"),
    ]
    for x0, w, fc in zones:
        ax.add_patch(mpatches.Rectangle(
            (x0 - 0.5, -0.5), w, H,
            facecolor=fc, alpha=0.35, linewidth=0, zorder=0,
        ))
    for bx in (W/3, 2*W/3):
        ax.axvline(x=bx - 0.5, color="#888888", linewidth=1.0,
                   linestyle="--", zorder=1, alpha=0.6)
    ax.set_xlim(-0.5, W - 0.5)
    ax.set_ylim(-0.5, H - 0.5)


# =============================================================================
# Légende
# =============================================================================

def make_legend(_model):
    return solara.Markdown("""
### Robots
| Symbole | Type | Zone |
|---------|------|------|
| ▲ Vert   | Collecte vert → jaune     | z1       |
| ■ Jaune  | Collecte jaune → rouge    | z1 + z2  |
| ◆ Rouge  | Transporte rouge → dépôt  | z1+z2+z3 |

### Déchets & Objets
| Symbole | Signification |
|---------|---------------|
| ● Vert   | Déchet vert  |
| ● Jaune  | Déchet jaune |
| ● Rouge  | Déchet rouge |
| ★ Bleu   | Zone de dépôt|
| ■ Noir   | Mur          |
""")


# =============================================================================
# Paramètres du modèle
# =============================================================================

model_params = {
    "communication": {
        "type": "Select",
        "value": True,
        "values": [True, False],
        "label": "Communication agents",
    },
    "n_green_waste": {
        "type": "SliderInt",
        "value": 20, "min": 5, "max": 50, "step": 5,
        "label": "Déchets verts (z1)",
    },
    "n_yellow_waste": {
        "type": "SliderInt",
        "value": 10, "min": 0, "max": 30, "step": 5,
        "label": "Déchets jaunes (z2)",
    },
    "n_red_waste": {
        "type": "SliderInt",
        "value": 5, "min": 0, "max": 20, "step": 1,
        "label": "Déchets rouges (z3)",
    },
    "n_walls": {
        "type": "SliderInt",
        "value": 40, "min": 0, "max": 80, "step": 5,
        "label": "Murs",
    },
    "n_green_robots": {
        "type": "SliderInt",
        "value": 3, "min": 1, "max": 6, "step": 1,
        "label": "Robots verts",
    },
    "n_yellow_robots": {
        "type": "SliderInt",
        "value": 3, "min": 1, "max": 6, "step": 1,
        "label": "Robots jaunes",
    },
    "n_red_robots": {
        "type": "SliderInt",
        "value": 3, "min": 1, "max": 6, "step": 1,
        "label": "Robots rouges",
    },
}

# =============================================================================
# Composants de visualisation
# =============================================================================

model = RobotMission()

SpaceGraph = make_space_component(
    agent_portrayal,
    post_process=zones_background,
)

WastePlot = make_plot_component({
    "Green Waste":  "#52b788",
    "Yellow Waste": "#f4a261",
    "Red Waste":    "#e63946",
    "Disposed":     "#023e8a",
})

# =============================================================================
# Page principale
# =============================================================================

page = SolaraViz(
    model,
    components=[make_legend, SpaceGraph, WastePlot],
    model_params=model_params,
    name="Self-Organization of Robots in a Hostile Environment",
)

page