import { describe, expect, it } from "vitest";

import { circleKey, circlePolygon, circlesToFeatureCollection, isCircleVisible, uniqueCircles } from "./circles";
import { EARTH_RADIUS_METERS, haversineMeters } from "./geodesy";

const RADII = [500, 1000, 2000];
const LATITUDES = [0, 39.4699, -33.87, 60, 80, 89];

describe("circlePolygon", () => {
  it.each(RADII.flatMap((radius) => LATITUDES.map((latitude) => [radius, latitude] as const)))(
    "radio %d m a la latitud %d: cada vértice está entre el 99 % y el 101 % del radio",
    (radius, latitude) => {
      const center = { latitude, longitude: -0.3763 };
      const ring = circlePolygon(center, radius, 64);
      for (const [longitude, vertexLatitude] of ring) {
        const distance = haversineMeters(center, { latitude: vertexLatitude!, longitude: longitude! });
        expect(distance).toBeGreaterThanOrEqual(radius * 0.99);
        expect(distance).toBeLessThanOrEqual(radius * 1.01);
      }
    },
  );

  it("cierra el anillo con 64 pasos y escribe longitud antes que latitud", () => {
    const ring = circlePolygon({ latitude: 39.4699, longitude: -0.3763 }, 1000, 64);
    expect(ring).toHaveLength(65);
    expect(ring[64]).toEqual(ring[0]);
    for (const [longitude, latitude] of ring) {
      expect(Math.abs(longitude! + 0.3763)).toBeLessThan(0.1);
      expect(Math.abs(latitude! - 39.4699)).toBeLessThan(0.1);
    }
  });

  it("no corta el polígono al cruzar el antimeridiano", () => {
    const ring = circlePolygon({ latitude: 0, longitude: 179.999 }, 2000, 64);
    for (let i = 1; i < ring.length; i += 1) {
      expect(Math.abs(ring[i]![0]! - ring[i - 1]![0]!)).toBeLessThan(1);
    }
  });
});

describe("circleKey", () => {
  const asset = { latitude: 39.469912, longitude: -0.376288, privacy_radius: 1000 };

  it("junta latitud, longitud y radio", () => {
    expect(circleKey(asset)).toBe("39.469912|-0.376288|1000");
  });

  it("cambia con el radio, la latitud o la longitud", () => {
    const keys = new Set([
      circleKey(asset),
      circleKey({ ...asset, privacy_radius: 2000 }),
      circleKey({ ...asset, latitude: 39.469913 }),
      circleKey({ ...asset, longitude: -0.376289 }),
    ]);
    expect(keys.size).toBe(4);
  });
});

describe("uniqueCircles", () => {
  const base = { latitude: 39.469912, longitude: -0.376288, privacy_radius: 1000 };

  it("da un solo círculo para la misma ubicación y el mismo radio", () => {
    expect(uniqueCircles([base, { ...base }, { ...base }])).toHaveLength(1);
  });

  it("da dos círculos concéntricos para radios distintos", () => {
    const circles = uniqueCircles([base, { ...base, privacy_radius: 2000 }]);
    expect(circles).toHaveLength(2);
    expect(circles.map((circle) => circle.radius)).toEqual([1000, 2000]);
  });

  it("conserva el orden de la primera aparición", () => {
    const other = { latitude: 39.5, longitude: -0.4, privacy_radius: 500 };
    const circles = uniqueCircles([other, base, other]);
    expect(circles.map((circle) => circle.key)).toEqual([circleKey(other), circleKey(base)]);
  });

  it("no da círculos para una lista vacía", () => {
    expect(uniqueCircles([])).toEqual([]);
  });
});

describe("circlesToFeatureCollection", () => {
  it("dibuja solo polígonos: sin marcador ni punto central", () => {
    const circles = uniqueCircles([
      { latitude: 39.47, longitude: -0.38, privacy_radius: 500 },
      { latitude: 39.47, longitude: -0.38, privacy_radius: 1000 },
    ]);
    const collection = circlesToFeatureCollection(circles);
    expect(collection.type).toBe("FeatureCollection");
    expect(collection.features).toHaveLength(2);
    expect(collection.features.map((feature) => feature.geometry.type)).toEqual(["Polygon", "Polygon"]);
    expect(collection.features[0]!.geometry.coordinates[0]).toHaveLength(65);
  });

  it("vacía la colección sin círculos", () => {
    expect(circlesToFeatureCollection([]).features).toEqual([]);
  });
});

describe("isCircleVisible", () => {
  const BOUNDS = { south: 39.4, north: 39.5, west: -0.45, east: -0.3 };
  const METERS_PER_DEGREE = (EARTH_RADIUS_METERS * Math.PI) / 180;
  const MIDDLE = { latitude: 39.45, longitude: -0.375 };
  const metersPerDegreeOfLongitude = (latitude: number) => METERS_PER_DEGREE * Math.cos((latitude * Math.PI) / 180);

  // Centro a los metros indicados de los bordes: positivo es hacia fuera
  const centerAt = (northMeters: number, eastMeters: number) => ({
    latitude: northMeters >= 0 ? BOUNDS.north + northMeters / METERS_PER_DEGREE : BOUNDS.south + northMeters / METERS_PER_DEGREE,
    longitude:
      eastMeters >= 0
        ? BOUNDS.east + eastMeters / metersPerDegreeOfLongitude(BOUNDS.north)
        : BOUNDS.west + eastMeters / metersPerDegreeOfLongitude(BOUNDS.north),
  });
  const circle = (center: { latitude: number; longitude: number }, radius: number) => ({ ...center, radius });

  it("ve un círculo con el centro dentro de la zona", () => {
    expect(isCircleVisible(circle(MIDDLE, 500), BOUNDS)).toBe(true);
  });

  it("ve un círculo de 2 km que asoma por el borde con el centro fuera", () => {
    expect(isCircleVisible(circle(centerAt(1500, 0), 2000), BOUNDS)).toBe(true);
  });

  it("no ve el círculo de 500 m ni el de 1 km a 1,5 km del borde", () => {
    expect(isCircleVisible(circle(centerAt(1500, 0), 500), BOUNDS)).toBe(false);
    expect(isCircleVisible(circle(centerAt(1500, 0), 1000), BOUNDS)).toBe(false);
  });

  // Centro a una distancia del borde indicado, a media altura o a media anchura de la zona
  const beyondEdge = {
    norte: (meters: number) => ({ latitude: BOUNDS.north + meters / METERS_PER_DEGREE, longitude: MIDDLE.longitude }),
    sur: (meters: number) => ({ latitude: BOUNDS.south - meters / METERS_PER_DEGREE, longitude: MIDDLE.longitude }),
    este: (meters: number) => ({
      latitude: MIDDLE.latitude,
      longitude: BOUNDS.east + meters / metersPerDegreeOfLongitude(MIDDLE.latitude),
    }),
    oeste: (meters: number) => ({
      latitude: MIDDLE.latitude,
      longitude: BOUNDS.west - meters / metersPerDegreeOfLongitude(MIDDLE.latitude),
    }),
  };

  it.each(["norte", "sur", "este", "oeste"] as const)("por el borde %s: asoma con el centro a 1 m menos del radio y no con 1 m más", (edge) => {
    expect(isCircleVisible(circle(beyondEdge[edge](999), 1000), BOUNDS)).toBe(true);
    expect(isCircleVisible(circle(beyondEdge[edge](1001), 1000), BOUNDS)).toBe(false);
  });

  it.each([
    ["noreste", 1, 1],
    ["noroeste", 1, -1],
    ["sureste", -1, 1],
    ["suroeste", -1, -1],
  ])("en la esquina %s cuenta la distancia a la esquina, no a cada borde", (_name, north, east) => {
    // A 800 m de cada borde (1131 m de la esquina): cada eje por separado cabría en 1 km, la esquina no
    expect(isCircleVisible(circle(centerAt(north * 800, east * 800), 1000), BOUNDS)).toBe(false);
    // A 700 m de cada borde (990 m de la esquina)
    expect(isCircleVisible(circle(centerAt(north * 700, east * 700), 1000), BOUNDS)).toBe(true);
  });

  it("ve un círculo tangente por dentro de un milímetro y no uno que se queda a un milímetro", () => {
    expect(isCircleVisible(circle(centerAt(1000 - 0.001, 0), 1000), BOUNDS)).toBe(true);
    expect(isCircleVisible(circle(centerAt(1000 + 0.001, 0), 1000), BOUNDS)).toBe(false);
  });

  it("ve un círculo que envuelve toda la zona sin tener el centro dentro", () => {
    const tiny = { south: 39.4, north: 39.4001, west: -0.4, east: -0.3999 };
    expect(isCircleVisible(circle({ latitude: 39.405, longitude: -0.4 }, 2000), tiny)).toBe(true);
  });
});
