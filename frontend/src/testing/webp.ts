export type WebpRejection =
  | "empty"
  | "too_large"
  | "not_webp"
  | "container_size"
  | "chunk_overflow"
  | "chunk_not_allowed"
  | "chunk_order"
  | "vp8x_size"
  | "vp8x_flags"
  | "image_header"
  | "dimensions"
  | "canvas"
  | "no_alpha";

export type WebpCheck = { ok: true } | { ok: false; code: WebpRejection };

type Chunk = { id: string; payload: number; size: number };
type Size = { width: number; height: number };
type ImageHeader = Size & { alphaIndicator: boolean };

const MAX_BYTES = 16_384;
const IMAGE_SIZE = 144;
const RIFF_HEADER_BYTES = 12;
const CHUNK_HEADER_BYTES = 8;
const VP8X_PAYLOAD_BYTES = 10;
const VP8_HEADER_BYTES = 10;
const VP8L_HEADER_BYTES = 5;
// Una cabecera de ALPH y al menos un byte de datos
const ALPH_MIN_BYTES = 2;
const VP8X_ALPHA_FLAG = 0x10;
// ICC, EXIF, XMP y animación: metadatos o fotogramas que una imagen de categoría no lleva
const VP8X_FORBIDDEN_FLAGS = 0x20 | 0x08 | 0x04 | 0x02;

const ALLOWED_CHUNKS = new Set(["VP8X", "ALPH", "VP8 ", "VP8L"]);
const VALID_SEQUENCES = [["VP8L"], ["VP8 "], ["VP8X", "VP8L"], ["VP8X", "VP8 "], ["VP8X", "ALPH", "VP8 "]];

const reject = (code: WebpRejection): WebpCheck => ({ ok: false, code });

function fourCC(view: DataView, offset: number): string {
  let text = "";
  for (let i = 0; i < 4; i += 1) text += String.fromCharCode(view.getUint8(offset + i));
  return text;
}

// Los tamaños se operan como números sin signo: 0xFFFFFFFF nunca puede volverse negativo
function readChunks(view: DataView): Chunk[] | null {
  const chunks: Chunk[] = [];
  let position = RIFF_HEADER_BYTES;
  while (position < view.byteLength) {
    if (position + CHUNK_HEADER_BYTES > view.byteLength) return null;
    const size = view.getUint32(position + 4, true);
    const end = position + CHUNK_HEADER_BYTES + size + (size % 2);
    if (end > view.byteLength) return null;
    chunks.push({ id: fourCC(view, position), payload: position + CHUNK_HEADER_BYTES, size });
    position = end;
  }
  return chunks;
}

function hasValidSequence(chunks: Chunk[]): boolean {
  return VALID_SEQUENCES.some(
    (sequence) => sequence.length === chunks.length && sequence.every((id, index) => id === chunks[index]?.id),
  );
}

function checkExtendedHeader(view: DataView, chunk: Chunk): WebpCheck | null {
  if (chunk.size !== VP8X_PAYLOAD_BYTES) return reject("vp8x_size");
  if (view.getUint8(chunk.payload) & VP8X_FORBIDDEN_FLAGS) return reject("vp8x_flags");
  return null;
}

// Fotograma clave con la firma 9D 01 2A; ancho y alto en los 14 bits bajos
function readLossyHeader(view: DataView, { payload, size }: Chunk): ImageHeader | null {
  if (size < VP8_HEADER_BYTES) return null;
  const isKeyFrame = (view.getUint8(payload) & 0x01) === 0;
  const hasSignature =
    view.getUint8(payload + 3) === 0x9d && view.getUint8(payload + 4) === 0x01 && view.getUint8(payload + 5) === 0x2a;
  if (!isKeyFrame || !hasSignature) return null;
  return {
    width: view.getUint16(payload + 6, true) & 0x3fff,
    height: view.getUint16(payload + 8, true) & 0x3fff,
    alphaIndicator: false,
  };
}

// Byte 0x2F y 32 bits: ancho menos uno, alto menos uno, indicador de alfa y versión
function readLosslessHeader(view: DataView, { payload, size }: Chunk): ImageHeader | null {
  if (size < VP8L_HEADER_BYTES || view.getUint8(payload) !== 0x2f) return null;
  const bits = view.getUint32(payload + 1, true);
  if (bits >>> 29 !== 0) return null;
  return {
    width: (bits & 0x3fff) + 1,
    height: ((bits >>> 14) & 0x3fff) + 1,
    alphaIndicator: ((bits >>> 28) & 0x01) === 1,
  };
}

const readImageHeader = (view: DataView, image: Chunk) =>
  image.id === "VP8L" ? readLosslessHeader(view, image) : readLossyHeader(view, image);

function readUint24(view: DataView, offset: number): number {
  return view.getUint8(offset) | (view.getUint8(offset + 1) << 8) | (view.getUint8(offset + 2) << 16);
}

// Ancho y alto del lienzo se guardan menos uno, en 24 bits cada uno
function readCanvas(view: DataView, extended: Chunk): Size {
  return { width: readUint24(view, extended.payload + 4) + 1, height: readUint24(view, extended.payload + 7) + 1 };
}

function hasTransparency(view: DataView, chunks: Chunk[], image: Chunk, header: ImageHeader, extended: Chunk | null) {
  if (extended === null) return header.alphaIndicator;
  if ((view.getUint8(extended.payload) & VP8X_ALPHA_FLAG) === 0) return false;
  if (image.id === "VP8L") return true;
  const alpha = chunks.find((chunk) => chunk.id === "ALPH");
  return alpha !== undefined && alpha.size >= ALPH_MIN_BYTES;
}

export function validateCategoryWebp(bytes: Uint8Array): WebpCheck {
  // El peso va antes que la estructura: un WebP bien formado mide siempre un número par de bytes
  if (bytes.length === 0) return reject("empty");
  if (bytes.length > MAX_BYTES) return reject("too_large");

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (bytes.length < RIFF_HEADER_BYTES || fourCC(view, 0) !== "RIFF" || fourCC(view, 8) !== "WEBP") {
    return reject("not_webp");
  }
  if (view.getUint32(4, true) + 8 !== bytes.length) return reject("container_size");

  const chunks = readChunks(view);
  if (chunks === null) return reject("chunk_overflow");
  if (!chunks.every((chunk) => ALLOWED_CHUNKS.has(chunk.id))) return reject("chunk_not_allowed");
  const image = chunks.find((chunk) => chunk.id === "VP8 " || chunk.id === "VP8L");
  if (image === undefined || !hasValidSequence(chunks)) return reject("chunk_order");

  const [first] = chunks;
  const extended = first?.id === "VP8X" ? first : null;
  if (extended !== null) {
    const problem = checkExtendedHeader(view, extended);
    if (problem !== null) return problem;
  }

  const header = readImageHeader(view, image);
  if (header === null) return reject("image_header");
  if (header.width !== IMAGE_SIZE || header.height !== IMAGE_SIZE) return reject("dimensions");

  // La imagen ya mide IMAGE_SIZE: el lienzo tiene que medir lo mismo
  const canvas = extended === null ? header : readCanvas(view, extended);
  if (canvas.width !== header.width || canvas.height !== header.height) return reject("canvas");

  return hasTransparency(view, chunks, image, header, extended) ? { ok: true } : reject("no_alpha");
}
