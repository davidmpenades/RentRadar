import { destinationPoint, distanceToBoundsMeters, type GeoPoint } from "./geodesy";
import type { VisibleBounds } from "./requestBox";

export type CircleSource = GeoPoint & { privacy_radius: number };

export type Circle = GeoPoint & { key: string; radius: number };

export type CircleCollection = {
  type: "FeatureCollection";
  features: {
    type: "Feature";
    properties: Record<string, never>;
    geometry: { type: "Polygon"; coordinates: number[][][] };
  }[];
};

// Anillo cerrado de [longitud, latitud]: el primer vértice se repite al final
export function circlePolygon(center: GeoPoint, radiusMeters: number, steps: number): number[][] {
  const ring: number[][] = [];
  for (let step = 0; step < steps; step += 1) {
    const point = destinationPoint(center, (2 * Math.PI * step) / steps, radiusMeters);
    ring.push([point.longitude, point.latitude]);
  }
  ring.push([...ring[0]!]);
  return ring;
}

export function circleKey(source: CircleSource): string {
  return `${source.latitude}|${source.longitude}|${source.privacy_radius}`;
}

// Los bienes con la misma ubicación pública y el mismo radio comparten círculo
export function uniqueCircles(sources: readonly CircleSource[]): Circle[] {
  const circles = new Map<string, Circle>();
  for (const source of sources) {
    const key = circleKey(source);
    if (!circles.has(key)) {
      circles.set(key, { key, latitude: source.latitude, longitude: source.longitude, radius: source.privacy_radius });
    }
  }
  return [...circles.values()];
}

// Una tarjeta por cada círculo que se ve aunque sea en parte: su punto más cercano de la zona cae dentro del radio
export function isCircleVisible(circle: GeoPoint & { radius: number }, bounds: VisibleBounds): boolean {
  return distanceToBoundsMeters(circle, bounds) <= circle.radius;
}

export function circlesToFeatureCollection(circles: readonly Circle[]): CircleCollection {
  return {
    type: "FeatureCollection",
    features: circles.map((circle) => ({
      type: "Feature",
      properties: {},
      geometry: { type: "Polygon", coordinates: [circlePolygon(circle, circle.radius, 64)] },
    })),
  };
}
