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

// El lienzo se guarda como ancho menos uno y alto menos uno, 24 bits cada uno
function vp8x(flags: number, payloadSize = 10, [width, height] = [SIZE, SIZE]): Uint8Array {
  return chunk("VP8X", fit([flags, 0, 0, 0, ...u24(width - 1), ...u24(height - 1)], payloadSize));
}

type Vp8Options = { width?: number; height?: number; tag?: number; signature?: number[] };

// Fotograma clave (bit 0 de la etiqueta a 0) con la firma 9D 01 2A y el tamaño en 14 bits
function vp8(payloadSize = 10, { width = SIZE, height = SIZE, tag = 0x10, signature = [0x9d, 0x01, 0x2a] }: Vp8Options = {}) {
  const header = [tag, 0, 0, ...signature, width & 0xff, (width >>> 8) & 0x3f, height & 0xff, (height >>> 8) & 0x3f];
  return chunk("VP8 ", fit(header, payloadSize));
}

type Vp8lOptions = { width?: number; height?: number; payloadSize?: number; signature?: number; version?: number };

// 0x2F, tamaño en 14 bits menos uno, indicador de alfa y versión en los 3 bits altos
function vp8l(alpha = true, { width = SIZE, height = SIZE, payloadSize = 5, signature = 0x2f, version = 0 }: Vp8lOptions = {}) {
  const bits = ((width - 1) | ((height - 1) << 14) | (alpha ? 1 << 28 : 0) | (version << 29)) >>> 0;
  return chunk("VP8L", fit([signature, ...u32(bits)], payloadSize));
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
    ["VP8L sin VP8X y con indicador de alfa", webp([vp8l()])],
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

const WRONG_SIZES = [
  [144, 143],
  [143, 144],
  [145, 144],
  [145, 145],
  [288, 288],
  [1024, 1024],
] as const;

// El lienzo de VP8X cuenta la misma mentira que la imagen, para que falle solo la imagen
const BAD_DIMENSIONS = WRONG_SIZES.flatMap(([width, height]): [WebpRejection, string, Uint8Array][] => [
  ["dimensions", `VP8 de ${width} × ${height}`, webp([vp8x(ALPHA, 10, [width, height]), alph(), vp8(10, { width, height })])],
  ["dimensions", `VP8L de ${width} × ${height}`, webp([vp8x(ALPHA, 10, [width, height]), vp8l(true, { width, height })])],
]);

// La imagen mide 144 × 144; lo que falla es el lienzo
const BAD_CANVAS: [WebpRejection, string, Uint8Array][] = [
  ["canvas", "VP8 con lienzo de 288 × 288", webp([vp8x(ALPHA, 10, [288, 288]), alph(), vp8()])],
  ["canvas", "VP8 con lienzo de 145 × 144", webp([vp8x(ALPHA, 10, [145, 144]), alph(), vp8()])],
  ["canvas", "VP8 con lienzo de 144 × 145", webp([vp8x(ALPHA, 10, [144, 145]), alph(), vp8()])],
  ["canvas", "VP8 con lienzo de 1 × 1", webp([vp8x(ALPHA, 10, [1, 1]), alph(), vp8()])],
  ["canvas", "VP8 con el lienzo máximo de 24 bits", webp([vp8x(ALPHA, 10, [2 ** 24, 2 ** 24]), alph(), vp8()])],
  ["canvas", "VP8L con lienzo de 288 × 288", webp([vp8x(ALPHA, 10, [288, 288]), vp8l()])],
  ["canvas", "VP8L con lienzo de 144 × 145", webp([vp8x(ALPHA, 10, [144, 145]), vp8l()])],
];

// Las cabeceras cortas vigilan que las lecturas no salgan de la carga del bloque
const BAD_HEADERS: [WebpRejection, string, Uint8Array][] = [
  ["image_header", "VP8 de 0 bytes", webp([vp8x(ALPHA), alph(), vp8(0)])],
  ["image_header", "VP8 de 9 bytes", webp([vp8x(ALPHA), alph(), vp8(9)])],
  ["image_header", "VP8 que no es un fotograma clave", webp([vp8x(ALPHA), alph(), vp8(10, { tag: 0x11 })])],
  ["image_header", "VP8 con el primer byte de la firma mal", webp([vp8x(ALPHA), alph(), vp8(10, { signature: [0x9c, 0x01, 0x2a] })])],
  ["image_header", "VP8 con el segundo byte de la firma mal", webp([vp8x(ALPHA), alph(), vp8(10, { signature: [0x9d, 0x00, 0x2a] })])],
  ["image_header", "VP8 con el tercer byte de la firma mal", webp([vp8x(ALPHA), alph(), vp8(10, { signature: [0x9d, 0x01, 0x2b] })])],
  ["image_header", "VP8L de 0 bytes", webp([vp8x(ALPHA), vp8l(true, { payloadSize: 0 })])],
  ["image_header", "VP8L de 4 bytes", webp([vp8x(ALPHA), vp8l(true, { payloadSize: 4 })])],
  ["image_header", "VP8L sin el byte 0x2F", webp([vp8x(ALPHA), vp8l(true, { signature: 0x2e })])],
  ["image_header", "VP8L de versión 1", webp([vp8x(ALPHA), vp8l(true, { version: 1 })])],
  ["image_header", "VP8L de versión 7", webp([vp8x(ALPHA), vp8l(true, { version: 7 })])],
];

const NO_ALPHA: [WebpRejection, string, Uint8Array][] = [
  ["no_alpha", "VP8 simple", webp([vp8()])],
  ["no_alpha", "VP8X sin bandera de alfa, con ALPH y VP8", webp([vp8x(0), alph(), vp8()])],
  ["no_alpha", "VP8X sin bandera de alfa y solo VP8", webp([vp8x(0), vp8()])],
  ["no_alpha", "VP8X sin bandera de alfa y VP8L con alfa", webp([vp8x(0), vp8l()])],
  ["no_alpha", "bandera de alfa sin ALPH", webp([vp8x(ALPHA), vp8()])],
  ["no_alpha", "ALPH de 1 byte", webp([vp8x(ALPHA), alph(1), vp8()])],
  ["no_alpha", "ALPH de 0 bytes", webp([vp8x(ALPHA), alph(0), vp8()])],
  ["no_alpha", "VP8L simple sin indicador de alfa", webp([vp8l(false)])],
];

describe("validateCategoryWebp: la imagen y su transparencia, cada caso por su causa", () => {
  it.each([...BAD_DIMENSIONS, ...BAD_CANVAS, ...BAD_HEADERS, ...NO_ALPHA])("%s: %s", (code, _name, bytes) => {
    expect(validateCategoryWebp(bytes)).toEqual({ ok: false, code });
  });
});
