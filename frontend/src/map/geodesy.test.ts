import { describe, expect, it } from "vitest";

import { destinationPoint, haversineMeters } from "./geodesy";

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
