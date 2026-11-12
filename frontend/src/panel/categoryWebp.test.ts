import { describe, expect, it } from "vitest";

import { validateCategoryWebp, type WebpRejection } from "../testing/webp";

const MAX_BYTES = 16_384;
const SIZE = 144;
const ALPHA = 0x10;
const ICC = 0x20;
const EXIF_FLAG = 0x08;
const XMP_FLAG = 0x04;
const ANIMATION = 0x02;

const encoder = new TextEncoder();

const u32 = (n: number) => [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff, (n >>> 24) & 0xff];
const u24 = (n: number) => [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff];
const zeros = (n: number) => new Array<number>(n).fill(0);

function concat(parts: ArrayLike<number>[]): Uint8Array {
  return Uint8Array.from(parts.flatMap((part) => Array.from(part)));
}

// Recorta o rellena con ceros hasta el tamaño pedido
function fit(payload: number[], size: number): number[] {
  return [...payload, ...zeros(Math.max(0, size - payload.length))].slice(0, size);
}

// El tamaño declarado se puede falsear; el relleno de los tamaños impares va siempre
function chunk(fourcc: string, payload: number[], declaredSize = payload.length): Uint8Array {
  return concat([encoder.encode(fourcc), u32(declaredSize), payload, payload.length % 2 === 1 ? [0] : []]);
}

function webp(chunks: Uint8Array[]): Uint8Array {
  const body = concat([encoder.encode("WEBP"), ...chunks]);
  return concat([encoder.encode("RIFF"), u32(body.length), body]);
}

function withRiffSize(bytes: Uint8Array, size: number): Uint8Array {
  const out = Uint8Array.from(bytes);
  new DataView(out.buffer).setUint32(4, size, true);
  return out;
}

// El contenedor declara exactamente lo que mide el fichero
const sealed = (bytes: Uint8Array) => withRiffSize(bytes, bytes.length - 8);

function withAscii(bytes: Uint8Array, offset: number, text: string): Uint8Array {
  const out = Uint8Array.from(bytes);
  out.set(encoder.encode(text), offset);
  return out;
}

function vp8x(flags: number, payloadSize = 10): Uint8Array {
  return chunk("VP8X", fit([flags, 0, 0, 0, ...u24(SIZE - 1), ...u24(SIZE - 1)], payloadSize));
}

// Fotograma clave con la firma 9D 01 2A y el tamaño en 14 bits
function vp8(payloadSize = 10): Uint8Array {
  const header = [0x10, 0, 0, 0x9d, 0x01, 0x2a, SIZE & 0xff, (SIZE >>> 8) & 0x3f, SIZE & 0xff, (SIZE >>> 8) & 0x3f];
  return chunk("VP8 ", fit(header, payloadSize));
}

// 0x2F, tamaño en 14 bits menos uno, indicador de alfa y versión 0
function vp8l(alpha = true): Uint8Array {
  const bits = ((SIZE - 1) | ((SIZE - 1) << 14) | (alpha ? 1 << 28 : 0)) >>> 0;
  return chunk("VP8L", [0x2f, ...u32(bits)]);
}

function alph(payloadSize = 2): Uint8Array {
  return chunk("ALPH", zeros(payloadSize));
}

const lossy = () => webp([vp8x(ALPHA), alph(), vp8()]);
const lossless = () => webp([vp8x(ALPHA), vp8l()]);

// Un WebP bien formado que mide exactamente `total` bytes (par: sin relleno)
function sizedTo(total: number): Uint8Array {
  const extra = total - lossy().length;
  return webp([vp8x(ALPHA), alph(), vp8(10 + extra)]);
}

describe("validateCategoryWebp: lo que se acepta", () => {
  it.each([
    ["VP8X + ALPH + VP8", lossy()],
    ["VP8X + VP8L", lossless()],
    ["el límite de peso exacto (16 384 bytes)", sizedTo(MAX_BYTES)],
    ["un ALPH de tamaño impar con su relleno", webp([vp8x(ALPHA), alph(3), vp8()])],
  ])("%s", (_name, bytes) => {
    expect(validateCategoryWebp(bytes)).toEqual({ ok: true });
  });

  it("los ejemplos tienen el tamaño que dicen", () => {
    expect(sizedTo(MAX_BYTES).length).toBe(MAX_BYTES);
    expect(sizedTo(MAX_BYTES + 2).length).toBe(MAX_BYTES + 2);
  });
});

const REJECTED: [WebpRejection, string, Uint8Array][] = [
  ["empty", "0 bytes", new Uint8Array(0)],

  ["too_large", "16 385 bytes (un byte más del límite)", concat([sizedTo(MAX_BYTES), [0]])],
  ["too_large", "16 386 bytes bien formado", sizedTo(MAX_BYTES + 2)],

  ["not_webp", "un PNG", concat([[0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a], zeros(32)])],
  ["not_webp", "un JPEG", concat([[0xff, 0xd8, 0xff, 0xe0], zeros(32)])],
  ["not_webp", "un SVG", encoder.encode('<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144"></svg>')],
  ["not_webp", "un RIFF que no es WEBP (WAVE)", withAscii(lossless(), 8, "WAVE")],
  ["not_webp", "RIFX en lugar de RIFF", withAscii(lossless(), 0, "RIFX")],
  ["not_webp", "menos de 12 bytes", encoder.encode("RIFF")],

  ["container_size", "datos detrás del contenedor", concat([lossless(), [0, 0, 0, 0]])],
  ["container_size", "contenedor que declara 2 bytes de más", withRiffSize(lossless(), lossless().length - 8 + 2)],
  ["container_size", "contenedor que declara 2 bytes de menos", withRiffSize(lossless(), lossless().length - 8 - 2)],
  ["container_size", "truncado sin ajustar el contenedor", lossy().slice(0, -6)],

  ["chunk_overflow", "truncado con el contenedor ajustado", sealed(lossy().slice(0, -6))],
  ["chunk_overflow", "bloque de 0xFFFFFFFF", webp([vp8x(ALPHA), chunk("VP8L", [0x2f, 0, 0, 0, 0], 0xffffffff)])],
  ["chunk_overflow", "bloque que declara más bytes de los que quedan", webp([vp8x(ALPHA), chunk("VP8L", [0x2f, 0, 0, 0, 0], 8)])],
  ["chunk_overflow", "menos de 8 bytes tras el último bloque", sealed(concat([lossless(), [1, 2, 3]]))],
  ["chunk_overflow", "bloque impar sin su relleno", webp([vp8x(ALPHA), chunk("ALPH", [0, 0, 0]).slice(0, -1)])],

  ["chunk_not_allowed", "EXIF", webp([vp8x(ALPHA), chunk("EXIF", [0, 0]), vp8()])],
  ["chunk_not_allowed", "XMP ", webp([vp8x(ALPHA), chunk("XMP ", [0, 0]), vp8()])],
  ["chunk_not_allowed", "ICCP", webp([vp8x(ALPHA), chunk("ICCP", [0, 0]), vp8()])],
  ["chunk_not_allowed", "un bloque desconocido", webp([vp8x(ALPHA), chunk("JUNK", [0, 0]), vp8()])],
  ["chunk_not_allowed", "un bloque desconocido sin VP8X", webp([chunk("JUNK", [0, 0]), vp8l()])],
  ["chunk_not_allowed", "animado (ANIM)", webp([vp8x(ALPHA), chunk("ANIM", zeros(6)), vp8()])],
  ["chunk_not_allowed", "animado (ANMF)", webp([vp8x(ALPHA), chunk("ANMF", zeros(16)), vp8()])],

  ["chunk_order", "dos imágenes (VP8 y VP8L)", webp([vp8x(ALPHA), vp8(), vp8l()])],
  ["chunk_order", "dos imágenes VP8L", webp([vp8l(), vp8l()])],
  ["chunk_order", "ALPH con VP8L y VP8X", webp([vp8x(ALPHA), alph(), vp8l()])],
  ["chunk_order", "ALPH con VP8L sin VP8X", webp([alph(), vp8l()])],
  ["chunk_order", "ALPH detrás de VP8", webp([vp8x(ALPHA), vp8(), alph()])],
  ["chunk_order", "ALPH sin VP8X", webp([alph(), vp8()])],
  ["chunk_order", "VP8X que no va primero", webp([alph(), vp8x(ALPHA), vp8()])],
  ["chunk_order", "VP8X detrás de la imagen", webp([vp8l(), vp8x(ALPHA)])],
  ["chunk_order", "dos VP8X", webp([vp8x(ALPHA), vp8x(ALPHA), vp8l()])],
  ["chunk_order", "solo VP8X", webp([vp8x(ALPHA)])],
  ["chunk_order", "ningún bloque", webp([])],

  ["vp8x_size", "VP8X de 0 bytes", webp([vp8x(ALPHA, 0), vp8l()])],
  ["vp8x_size", "VP8X de 9 bytes", webp([vp8x(ALPHA, 9), vp8l()])],
  ["vp8x_size", "VP8X de 11 bytes", webp([vp8x(ALPHA, 11), vp8l()])],
  ["vp8x_size", "VP8X de 12 bytes", webp([vp8x(ALPHA, 12), vp8l()])],

  ["vp8x_flags", "bandera de ICC sin su bloque", webp([vp8x(ALPHA | ICC), vp8l()])],
  ["vp8x_flags", "bandera de EXIF sin su bloque", webp([vp8x(ALPHA | EXIF_FLAG), vp8l()])],
  ["vp8x_flags", "bandera de XMP sin su bloque", webp([vp8x(ALPHA | XMP_FLAG), vp8l()])],
  ["vp8x_flags", "bandera de animación sin su bloque", webp([vp8x(ALPHA | ANIMATION), vp8l()])],
  ["vp8x_flags", "las cuatro banderas a la vez", webp([vp8x(ALPHA | ICC | EXIF_FLAG | XMP_FLAG | ANIMATION), vp8l()])],
];

describe("validateCategoryWebp: lo que se rechaza, cada caso por su causa", () => {
  it.each(REJECTED)("%s: %s", (code, _name, bytes) => {
    expect(validateCategoryWebp(bytes)).toEqual({ ok: false, code });
  });

  it("cada prefijo de un WebP válido se rechaza sin lanzar", () => {
    const valid = lossy();
    for (let length = 0; length < valid.length; length += 1) {
      expect(validateCategoryWebp(valid.slice(0, length)).ok).toBe(false);
    }
  });
});
