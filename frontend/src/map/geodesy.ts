import type { VisibleBounds } from "./requestBox";

export type GeoPoint = { latitude: number; longitude: number };

export const EARTH_RADIUS_METERS = 6_371_008.8;

const toRadians = (degrees: number) => (degrees * Math.PI) / 180;
const toDegrees = (radians: number) => (radians * 180) / Math.PI;

export function haversineMeters(a: GeoPoint, b: GeoPoint): number {
  const latitudeA = toRadians(a.latitude);
  const latitudeB = toRadians(b.latitude);
  const deltaLatitude = latitudeB - latitudeA;
  const deltaLongitude = toRadians(b.longitude - a.longitude);
  const h =
    Math.sin(deltaLatitude / 2) ** 2 +
    Math.cos(latitudeA) * Math.cos(latitudeB) * Math.sin(deltaLongitude / 2) ** 2;
  return 2 * EARTH_RADIUS_METERS * Math.asin(Math.min(1, Math.sqrt(h)));
}

// La longitud no se normaliza: el polígono de un círculo debe ser continuo al cruzar el antimeridiano
export function destinationPoint(origin: GeoPoint, bearingRadians: number, distanceMeters: number): GeoPoint {
  const angularDistance = distanceMeters / EARTH_RADIUS_METERS;
  const latitude = toRadians(origin.latitude);
  const destinationLatitude = Math.asin(
    Math.sin(latitude) * Math.cos(angularDistance) +
      Math.cos(latitude) * Math.sin(angularDistance) * Math.cos(bearingRadians),
  );
  const destinationLongitude =
    toRadians(origin.longitude) +
    Math.atan2(
      Math.sin(bearingRadians) * Math.sin(angularDistance) * Math.cos(latitude),
      Math.cos(angularDistance) - Math.sin(latitude) * Math.sin(destinationLatitude),
    );
  return { latitude: toDegrees(destinationLatitude), longitude: toDegrees(destinationLongitude) };
}

const clamp = (value: number, low: number, high: number) => Math.min(Math.max(value, low), high);

// Recortar latitud y longitud por separado da el punto más cercano con un error de centímetros a estas distancias
export function distanceToBoundsMeters(point: GeoPoint, bounds: VisibleBounds): number {
  const nearest = {
    latitude: clamp(point.latitude, bounds.south, bounds.north),
    longitude: clamp(point.longitude, bounds.west, bounds.east),
  };
  return haversineMeters(point, nearest);
}
