import math
import random

import pytest

from apps.assets.location import _project, _unproject

BOX_CORNERS = [(27.5, -18.5), (27.5, 5.0), (44.0, -18.5), (44.0, 5.0)]
CITIES_AND_ISLANDS = [
    (28.1235, -15.4363),  # Las Palmas
    (28.68, -17.76),  # La Palma
    (27.74, -18.16),  # El Hierro
    (39.5696, 2.6502),  # Palma
    (38.9067, 1.4206),  # Ibiza
    (40.4168, -3.7038),  # Madrid
    (38.7223, -9.1393),  # Lisboa
    (42.5063, 1.5218),  # Andorra
    (43.6047, 1.4442),  # Toulouse
]
CELL_SIDE = 2000
# Metros desde la esquina inferior izquierda de una celda de 2000 m
EDGE_OFFSETS = [
    (0.01, 0.01),
    (CELL_SIDE - 0.01, 0.01),
    (0.01, CELL_SIDE - 0.01),
    (CELL_SIDE - 0.01, CELL_SIDE - 0.01),
    (1000, 0.01),
    (0.01, 1000),
    (-0.01, -0.01),
    (CELL_SIDE + 0.01, 1000),
]
RANDOM_POINTS = 200


def points_around_cell_edges(latitude, longitude):
    east, north = _project(latitude, longitude)
    base_east = math.floor(east / CELL_SIDE) * CELL_SIDE
    base_north = math.floor(north / CELL_SIDE) * CELL_SIDE
    return [
        _unproject(base_east + offset_east, base_north + offset_north)
        for offset_east, offset_north in EDGE_OFFSETS
    ]


@pytest.fixture(scope="session")
def sample_points():
    generator = random.Random(5)
    random_points = [
        (generator.uniform(27.5, 44.0), generator.uniform(-18.5, 5.0))
        for _ in range(RANDOM_POINTS)
    ]
    edge_points = [
        point
        for reference in [(40.4168, -3.7038), (28.1235, -15.4363), (39.5696, 2.6502)]
        for point in points_around_cell_edges(*reference)
    ]
    return tuple(BOX_CORNERS + CITIES_AND_ISLANDS + edge_points + random_points)
