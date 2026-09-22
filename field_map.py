# field_map.py
# Mapa de navegación y waypoints de Reefscape en MoSimulator

WAYPOINTS = {
    "human_izq": {"name": "Human izquierda", "x": 7.30, "z": 2.74, "yaw": 41.3},
    "human_der": {"name": "Human derecha", "x": 7.28, "z": -2.61, "yaw": 313.8},
    "reef_1":    {"name": "Cara reef 1",     "x": 5.80, "z": 0.20, "yaw": 272.2},
    "reef_2":    {"name": "Cara reef 2",     "x": 4.99, "z": 1.22, "yaw": 209.3},
    "reef_3":    {"name": "Cara reef 3",     "x": 3.54, "z": 1.18, "yaw": 150.1},
    "reef_4":    {"name": "Cara reef 4",     "x": 2.92, "z": 0.03, "yaw": 90.4},
    "reef_5":    {"name": "Cara reef 5",     "x": 3.56, "z": -1.27, "yaw": 34.9},
    "reef_6":    {"name": "Cara reef 6",     "x": 4.99, "z": -1.32, "yaw": 329.3},
    "centro":    {"name": "Centro cancha",   "x": 1.16, "z": 0.01, "yaw": 90.6},
}

def get_waypoint(key: str) -> dict:
    return WAYPOINTS.get(key, WAYPOINTS["centro"])