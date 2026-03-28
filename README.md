# Self-Organization of Robots in a Hostile Environment

**Multi-Agent System — CentraleSupélec MAS 2025-2026**

---

## Table des matières

1. [Présentation du projet](#1-présentation-du-projet)
2. [Structure du projet](#2-structure-du-projet)
3. [Environnement et zones](#3-environnement-et-zones)
4. [Types de robots et de déchets](#4-types-de-robots-et-de-déchets)
5. [Chaîne de transformation](#5-chaîne-de-transformation)
6. [Boucle percept → délibérer → agir](#6-boucle-percept--délibérer--agir)
7. [Navigation par BFS](#7-navigation-par-bfs)
8. [Stratégie de communication](#8-stratégie-de-communication)
9. [Actions et model.do()](#9-actions-et-modeldo)
10. [Installation et lancement](#10-installation-et-lancement)
11. [Métriques](#11-métriques)

---

## 1. Présentation du projet

Ce projet simule une mission de collecte et de traitement de déchets radioactifs par des robots autonomes dans un environnement hostile. Les robots doivent collaborer pour collecter, transformer et transporter les déchets vers une zone de dépôt finale, en respectant des contraintes de zones et de radioactivité.

La simulation est implémentée avec le framework **Mesa** (Python) et visualisée avec **Solara**. Elle illustre les concepts fondamentaux des systèmes multi-agents : perception, délibération, action, mémoire et communication.

---

## 2. Structure du projet

```
.
├── .gitignore
├── README.md
├── requirements.txt
├── run.py                 # Lanceur headless en ligne de commande
├── server.py              # Visualisation Solara (zones, graphes, légende)
└── src/
    ├── __init__.py
    ├── agents.py          # Classe Robot — boucle percept/délibérer/agir
    ├── communication.py   # Système de messagerie entre agents
    ├── model.py           # Environnement, validation et exécution des actions (do)
    └── objects.py         # Objets passifs : Waste, Wall, DisposalZone, Radioactivity
```

| Fichier | Rôle | Classes principales |
|---|---|---|
| `src/agents.py` | Logique décisionnelle complète de chaque robot | `Robot` |
| `src/model.py` | Grille, placement des agents, méthode `do()` | `RobotMission` |
| `src/objects.py` | Agents passifs sans comportement | `Waste`, `Wall`, `DisposalZone`, `Radioactivity` |
| `src/communication.py` | Boîte aux lettres centrale | `CommunicationSystem`, `Message` |
| `server.py` | Interface Solara avec zones colorées et métriques | — |
| `run.py` | Simulation sans GUI avec sortie console | — |

---

## 3. Environnement et zones

La grille est de **30×30 cases**, divisée en 3 zones verticales selon le niveau de radioactivité :

| Zone | Colonnes | Radioactivité | Contenu initial |
|---|---|---|---|
| 🟩 z1 (verte) | `x ∈ [0, W/3)` | Faible (0.0 – 0.33) | Déchets verts + robots verts |
| 🟨 z2 (jaune) | `x ∈ [W/3, 2W/3)` | Moyenne (0.33 – 0.66) | Déchets jaunes + robots jaunes |
| 🟥 z3 (rouge) | `x ∈ [2W/3, W)` | Haute (0.66 – 1.0) | Déchets rouges + robots rouges + DisposalZone |

Chaque cellule contient un agent `Radioactivity` passif dont le niveau est tiré aléatoirement dans la plage de sa zone. Des murs (`Wall`) sont placés aléatoirement, jamais sur les colonnes frontières `W/3` et `2W/3` pour garantir le passage entre zones.

---

## 4. Types de robots et de déchets

### 4.1 Les trois types de déchets

| Type | Couleur | Origine |
|---|---|---|
| Green | 🟢 Vert | Présent dès le départ en z1 |
| Yellow | 🟡 Jaune | Présent en z2 + créé par transformation de 2 verts |
| Red | 🔴 Rouge | Présent en z3 + créé par transformation de 2 jaunes |

### 4.2 Les trois types de robots

| Robot | Symbole | Zone autorisée | Mission |
|---|---|---|---|
| Vert | ▲ Triangle | z1 uniquement `x < W/3` | Collecte 2 verts → transforme en 1 jaune → dépose à `x=W/3` |
| Jaune | ■ Carré | z1 + z2 `x < 2W/3` | Collecte 2 jaunes → transforme en 1 rouge → dépose à `x=2W/3` |
| Rouge | ◆ Diamant | z1 + z2 + z3 (tout) | Collecte 1 rouge → transporte à la DisposalZone ★ → élimine |

---

## 5. Chaîne de transformation

La mission suit une pipeline séquentielle en 3 étapes :

```
🟢 Robot vert (z1)
   ├── collecte 2 déchets verts
   ├── TRANSFORM → 1 jaune dans l'inventaire
   ├── BFS vers x = W/3
   └── DROP → déchet jaune posé sur la grille
            ↓
🟡 Robot jaune (z1 + z2)
   ├── collecte 2 déchets jaunes
   ├── TRANSFORM → 1 rouge dans l'inventaire
   ├── BFS vers x = 2W/3
   └── DROP → déchet rouge posé sur la grille
            ↓
🔴 Robot rouge (z1 + z2 + z3)
   ├── collecte 1 déchet rouge
   ├── BFS vers DisposalZone (★ colonne x = W-1)
   └── DROP → déchet définitivement éliminé
              waste_counts["disposed"] += 1
```

Les transformations se font entièrement en mémoire (dans l'inventaire). Le déchet n'apparaît physiquement sur la grille qu'au moment du `DROP`.

---

## 6. Boucle percept → délibérer → agir

À chaque step, chaque robot exécute la méthode `step()` :

```python
def step(self):
    percepts     = self._perceive()              # Observer le voisinage (Moore rayon 1)
    self._update_knowledge(percepts)             # Mettre à jour la base de connaissances
    action       = self._deliberate(self.knowledge)  # Choisir une action
    new_percepts = self.model.do(self, action)   # Exécuter l'action via le modèle
    self._update_knowledge(new_percepts)         # Intégrer le feedback
    self.knowledge["last_action"] = action["type"]
```

### 6.1 Perception

Le robot perçoit toutes les cases dans son **voisinage Moore de rayon 1** (8 voisins + case actuelle). Il obtient un dictionnaire `{(x,y): [liste d'objets]}` pour chaque case perçue.

### 6.2 Base de connaissances (`self.knowledge`)

```python
self.knowledge = {
    "pos":          None,      # position courante (x, y)
    "inventory":    [],        # liste des déchets portés
    "carrying":     0,         # len(inventory)
    "percepts":     {},        # dernière perception
    "known_waste":  {},        # {(x,y): waste_type} — mémoire des déchets vus
    "disposal_pos": None,      # position de la DisposalZone
    "last_action":  WAIT,
    "steps_idle":   0,         # compteur anti-blocage
}
```

### 6.3 Délibération — 6 priorités ordonnées

La fonction `_deliberate()` est une **fonction pure** sur le `knowledge`. Elle suit 6 priorités strictement ordonnées et s'arrête à la première qui dit "oui" :

| Priorité | Condition | Action |
|---|---|---|
| 1 | Inventaire contient ≥ N déchets cibles | `TRANSFORM` |
| 2 | Robot rouge + rouge en inventaire | `BFS → DisposalZone → DROP` |
| 3 | Produit transformé en inventaire | `BFS → frontière zone → DROP` |
| 4 | Déchet cible sur la case actuelle | `PICK` |
| 5 | known_waste contient une cible connue | `BFS → position cible` |
| 6 | Aucune des conditions précédentes | Exploration aléatoire |

---

## 7. Navigation par BFS

La navigation utilise un algorithme **BFS (Breadth-First Search)** au lieu d'un déplacement glouton. Cela permet au robot de trouver le chemin optimal en **contournant automatiquement** les murs et les frontières de zone.

```python
def _bfs_move(self, target, k, relaxed):
    visited = {pos: None}
    queue   = deque([pos])
    while queue:
        cur = queue.popleft()
        if cur == target: break
        for voisin in moore_neighbours(cur):
            if voisin not in visited and self._walkable(voisin, relaxed):
                visited[voisin] = cur
                queue.append(voisin)
    # Retourner le premier pas du chemin optimal
```

Le paramètre `relaxed=True` autorise le robot à franchir d'**une colonne** sa limite de zone, uniquement lors du dépôt du déchet transformé à la frontière.

La contrainte de zone est vérifiée **en double** : dans `_walkable()` côté agent ET dans `model.do()` côté environnement, avec des formules identiques :

```python
# Zone enforcement (identique dans agents.py et model.py)
extra = 1 if relaxed else 0
if robot_type == "green"  and x >= W//3     + extra: return False
if robot_type == "yellow" and x >= 2*W//3   + extra: return False
# red : aucune restriction
```

---

## 8. Stratégie de communication

Le système repose sur une philosophie de **messages ciblés** : chaque agent n'envoie des informations qu'aux agents qui en ont réellement besoin.

### 8.1 Le CommunicationSystem

Boîte aux lettres centrale attachée au modèle (`model.communication_system`). Maintient un dictionnaire `_inbox` : `{agent_id: [messages]}`.

Trois modes de livraison :

- `send(message)` — envoi point-à-point vers un destinataire précis
- `send_to_group(message, agent_ids)` — envoi ciblé vers une liste d'agents
- `broadcast(message)` — diffusion à tous (clé `None`), purgée à la fin de chaque step

### 8.2 Les 3 types de messages

| Message | Déclencheur | Destinataires |
|---|---|---|
| `INFORM_WASTE` | Un robot voit un déchet qui n'est pas son type cible | Robots du type responsable uniquement |
| `INFORM_COLLECTED` | Un robot ramasse un déchet (`PICK` réussi) | Broadcast tous robots |
| `DISPOSAL_POS` | Un robot aperçoit la DisposalZone | Robots rouges uniquement |

### 8.3 Exemple concret

```
Step 1 : Robot vert en (7,14) perçoit déchet jaune en (9,14)
         → envoie INFORM_WASTE aux 3 robots jaunes uniquement

Step 2 : Les robots jaunes lisent leur inbox
         → ajoutent (9,14):"yellow" à leur known_waste

Step 3 : Le robot jaune le plus proche calcule BFS vers (9,14)
         → s'y dirige directement sans explorer

Step 4 : Le robot jaune ramasse le déchet
         → broadcast INFORM_COLLECTED
         → les 2 autres robots jaunes retirent (9,14) de leur mémoire
```

### 8.4 Initialisation des robots rouges

La position de la `DisposalZone` est **pré-remplie** dans le knowledge de tous les robots rouges à l'initialisation du modèle :

```python
for agent in self.agents:
    if isinstance(agent, Robot) and agent.robot_type == "red":
        agent.knowledge["disposal_pos"] = self._disposal_pos
```

Cela évite que les robots rouges perdent du temps à explorer pour trouver la zone de dépôt.

### 8.5 Purge des entrées périmées

À chaque `_update_knowledge()`, chaque robot vérifie directement dans la grille si les positions mémorisées contiennent encore un déchet. Si la case est vide, la position est retirée de `known_waste` :

```python
stale = [p for p in known_waste if not any(isinstance(o, Waste)
         for o in grid.get_cell_list_contents(p))]
for p in stale:
    del known_waste[p]
```

---

## 9. Actions et `model.do()`

Le modèle est l'**arbitre** de toutes les actions. La méthode `do(agent, action)` valide chaque action avant de l'exécuter et retourne les nouveaux percepts.

| Action | Condition de validité | Effet |
|---|---|---|
| `MOVE` | Case adjacente, dans la zone, sans mur | Déplace le robot |
| `PICK` | Déchet cible sur la case, inventaire non plein | Retire le déchet de la grille |
| `TRANSFORM` | Inventaire ≥ N déchets cibles | Remplace N cibles par 1 produit |
| `DROP` | Inventaire non vide | Dépose sur grille (ou dispose si rouge à DisposalZone) |
| `WAIT` | Toujours valide | Ne fait rien |

---

## 10. Installation et lancement

### 10.1 Prérequis

- Python 3.11 ou 3.12
- Venv Python **sans** Anaconda actif (`conda deactivate` avant)

### 10.2 Installation

```powershell
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install mesa==3.1.4 solara matplotlib pandas
```

### 10.3 Lancement de la visualisation

```powershell
solara run server.py
```

Puis ouvrir **http://localhost:8765** dans le navigateur.

### 10.4 Lancement headless (sans GUI)

```powershell
python run.py                     # 200 steps par défaut
python run.py --steps 500         # 500 steps
python run.py --steps 300 --csv   # sauvegarde results.csv
python run.py --no-comm           # sans communication entre agents
```

### 10.5 Paramètres configurables dans l'interface

- Communication agents (activée / désactivée)
- Nombre de déchets verts / jaunes / rouges initiaux
- Nombre de murs
- Nombre de robots par type (1 à 6)

---

## 11. Métriques

Le `DataCollector` de Mesa enregistre à chaque step :

| Métrique | Description |
|---|---|
| `Green Waste` | Déchets verts restants sur la grille |
| `Yellow Waste` | Déchets jaunes en circulation |
| `Red Waste` | Déchets rouges en circulation |
| `Disposed` | Total des déchets définitivement éliminés |
| `Total Waste` | Somme des trois types en circulation |

Ces métriques sont affichées en temps réel dans le graphe sous la grille. Avec `--csv`, elles sont exportées dans `results.csv`.

---

*CentraleSupélec — MAS 2025-2026*