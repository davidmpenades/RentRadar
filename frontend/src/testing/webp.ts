export type WebpRejection =
  | "empty"
  | "too_large"
  | "not_webp"
  | "container_size"
  | "chunk_overflow"
  | "chunk_not_allowed"
  | "chunk_order"
  | "vp8x_size"
  | "vp8x_flags";

export type WebpCheck = { ok: true } | { ok: false; code: WebpRejection };

type Chunk = { id: string; payload: number; size: number };

const MAX_BYTES = 16_384;
const RIFF_HEADER_BYTES = 12;
const CHUNK_HEADER_BYTES = 8;
const VP8X_PAYLOAD_BYTES = 10;
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
  if (!hasValidSequence(chunks)) return reject("chunk_order");

  const [first] = chunks;
  if (first?.id === "VP8X") return checkExtendedHeader(view, first) ?? { ok: true };
  return { ok: true };
}
