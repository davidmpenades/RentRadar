import { describe, expect, it } from "vitest";

import { circleKey, circlePolygon, circlesToFeatureCollection, uniqueCircles } from "./circles";
import { haversineMeters } from "./geodesy";

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
