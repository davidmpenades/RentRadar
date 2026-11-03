import { describe, expect, it } from "vitest";

import { destinationPoint, distanceToBoundsMeters, haversineMeters } from "./geodesy";

const METERS_PER_DEGREE = 111_195.08;

describe("haversineMeters", () => {
  it("vale cero entre un punto y él mismo", () => {
    expect(haversineMeters({ latitude: 39.47, longitude: -0.38 }, { latitude: 39.47, longitude: -0.38 })).toBe(0);
  });

  it("mide un grado de meridiano y un grado de ecuador", () => {
    const origin = { latitude: 0, longitude: 0 };
    expect(haversineMeters(origin, { latitude: 1, longitude: 0 })).toBeCloseTo(METERS_PER_DEGREE, 0);
    expect(haversineMeters(origin, { latitude: 0, longitude: 1 })).toBeCloseTo(METERS_PER_DEGREE, 0);
  });

  it("es simétrica", () => {
    const a = { latitude: 39.47, longitude: -0.38 };
    const b = { latitude: 41.39, longitude: 2.17 };
    expect(haversineMeters(a, b)).toBeCloseTo(haversineMeters(b, a), 6);
  });

  it("acorta la longitud lejos del ecuador", () => {
    const meters = haversineMeters({ latitude: 60, longitude: 0 }, { latitude: 60, longitude: 1 });
    expect(meters).toBeCloseTo(METERS_PER_DEGREE / 2, -1);
  });

  it("mide bien a través del antimeridiano", () => {
    const meters = haversineMeters({ latitude: 0, longitude: 179.5 }, { latitude: 0, longitude: -179.5 });
    expect(meters).toBeCloseTo(METERS_PER_DEGREE, 0);
  });
});

describe("destinationPoint", () => {
  it("hacia el norte sube la latitud y conserva la longitud", () => {
    const point = destinationPoint({ latitude: 39.47, longitude: -0.38 }, 0, 1000);
    expect(point.latitude).toBeCloseTo(39.47 + 1000 / METERS_PER_DEGREE, 5);
    expect(point.longitude).toBeCloseTo(-0.38, 9);
  });

  it("hacia el este conserva la latitud en el ecuador", () => {
    const point = destinationPoint({ latitude: 0, longitude: 10 }, Math.PI / 2, 1000);
    expect(point.latitude).toBeCloseTo(0, 9);
    expect(point.longitude).toBeCloseTo(10 + 1000 / METERS_PER_DEGREE, 5);
  });

  it.each([0, 1, 2.5, 4, 6])("queda a la distancia pedida con el rumbo %d rad", (bearing) => {
    const origin = { latitude: 39.4699, longitude: -0.3763 };
    const point = destinationPoint(origin, bearing, 2000);
    expect(haversineMeters(origin, point)).toBeCloseTo(2000, 3);
  });
});

describe("distanceToBoundsMeters", () => {
  const BOUNDS = { south: 39.4, north: 39.5, west: -0.45, east: -0.3 };

  it("vale cero dentro de la zona y sobre su borde", () => {
    expect(distanceToBoundsMeters({ latitude: 39.45, longitude: -0.375 }, BOUNDS)).toBe(0);
    expect(distanceToBoundsMeters({ latitude: 39.5, longitude: -0.3 }, BOUNDS)).toBe(0);
  });

  it("mide hacia el norte la distancia al meridiano del borde", () => {
    const meters = distanceToBoundsMeters({ latitude: 39.51, longitude: -0.375 }, BOUNDS);
    expect(meters).toBeCloseTo(0.01 * METERS_PER_DEGREE, 3);
  });

  // Referencia: el punto más cercano de los cuatro bordes, buscado por muestreo denso
  function nearestOnEdges(point: { latitude: number; longitude: number }, bounds: typeof BOUNDS): number {
    const steps = 2000;
    let best = Infinity;
    for (let step = 0; step <= steps; step += 1) {
      const t = step / steps;
      const latitude = bounds.south + (bounds.north - bounds.south) * t;
      const longitude = bounds.west + (bounds.east - bounds.west) * t;
      for (const edgePoint of [
        { latitude, longitude: bounds.west },
        { latitude, longitude: bounds.east },
        { latitude: bounds.south, longitude },
        { latitude: bounds.north, longitude },
      ]) {
        best = Math.min(best, haversineMeters(point, edgePoint));
      }
    }
    return best;
  }

  // Recortar latitud y longitud por separado no da exactamente el punto más cercano de un meridiano: aquí se fija cuánto se desvía
  it.each([0, 39.47, 60, 80])(
    "a la latitud %d el recorte por separado se desvía menos de 5 cm del punto más cercano (0,01 % de 500 m)",
    (latitude) => {
      const bounds = { south: latitude - 0.1, north: latitude + 0.1, west: -0.2, east: 0.2 };
      const metersPerDegreeOfLongitude = METERS_PER_DEGREE * Math.cos((latitude * Math.PI) / 180);
      let worst = 0;
      for (const outside of [100, 500, 1000, 2000, 4000]) {
        for (const alongDegrees of [-0.15, -0.1, 0, 0.05, 0.1, 0.15]) {
          const points = [
            { latitude: latitude + alongDegrees, longitude: bounds.east + outside / metersPerDegreeOfLongitude },
            { latitude: latitude + alongDegrees, longitude: bounds.west - outside / metersPerDegreeOfLongitude },
            { latitude: bounds.north + outside / METERS_PER_DEGREE, longitude: alongDegrees },
            { latitude: bounds.south - outside / METERS_PER_DEGREE, longitude: alongDegrees },
          ];
          for (const point of points) {
            worst = Math.max(worst, Math.abs(distanceToBoundsMeters(point, bounds) - nearestOnEdges(point, bounds)));
          }
        }
      }
      expect(worst).toBeLessThan(0.05);
    },
  );
});
