import { z } from "zod";

import type { components } from "./schema.gen";

type PublicAssetList = components["schemas"]["PublicAssetList"];

const MAX_ASSETS = 200;

// Los máximos de texto son más holgados que los del servidor para no rechazar la lista si el backend sube un límite
export const publicAssetSchema = z.strictObject({
  public_id: z.uuidv4(),
  title: z
    .string()
    .max(200)
    .refine((value) => value.trim().length > 0),
  category_slug: z.string().min(1).max(64),
  category_name: z.string().min(1).max(100),
  price: z.string().regex(/^\d{1,5}\.\d{2}$/),
  currency: z.literal("EUR"),
  price_unit: z.enum(["hour", "day", "week", "month"]),
  privacy_radius: z.union([z.literal(500), z.literal(1000), z.literal(2000)]),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
});

export const publicAssetListSchema = z.strictObject({
  results: z
    .array(publicAssetSchema)
    .max(MAX_ASSETS)
    .refine((assets) => new Set(assets.map((asset) => asset.public_id)).size === assets.length),
  incomplete: z.boolean(),
});

export class InvalidResponseError extends Error {
  constructor() {
    super("La respuesta de la API no tiene la forma esperada");
  }
}

// Si un bien falla, la respuesta entera es inválida; el error no lleva ni los valores ni los problemas de Zod
export function validateResponse(json: unknown): PublicAssetList {
  const parsed = publicAssetListSchema.safeParse(json);
  if (!parsed.success) throw new InvalidResponseError();
  // Comprueba en compilación que el esquema cabe en el tipo generado
  return parsed.data;
}
