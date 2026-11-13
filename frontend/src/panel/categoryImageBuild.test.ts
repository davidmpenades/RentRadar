import { build, type Plugin } from "vite";
import { beforeAll, describe, expect, it } from "vitest";

import { CATEGORY_KEYS } from "../testing/categoryKeys";

// Raíz del frontend; no hay tipos de Node, así que no se usa process ni node:path
const root = decodeURIComponent(new URL("../..", import.meta.url).pathname);
// Umbral de incrustación muy por encima del peso de cualquier imagen
const HUGE_INLINE_LIMIT = 1_000_000;
const CONTROL_ENTRY = "virtual:category-image-control";

const CATEGORY_DIR = "/assets/categories/";

function fileNameOf(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1);
}

function textOf(source: string | Uint8Array): string {
  return typeof source === "string" ? source : new TextDecoder().decode(source);
}

function emittedOf(result: Awaited<ReturnType<typeof build>>) {
  const outputs = Array.isArray(result) ? result : "output" in result ? [result] : [];
  return outputs.flatMap((one) => one.output);
}

type Emitted = ReturnType<typeof emittedOf>;

function assetsOf(items: Emitted) {
  return items.filter((item) => item.type === "asset");
}

function chunksOf(items: Emitted) {
  return items.filter((item) => item.type === "chunk");
}

// Entrada mínima que importa una imagen real sin la consulta ?no-inline
const controlEntry: Plugin = {
  name: "category-image-control-entry",
  resolveId(id) {
    return id === CONTROL_ENTRY ? `\0${CONTROL_ENTRY}` : null;
  },
  load(id) {
    if (id !== `\0${CONTROL_ENTRY}`) return null;
    return 'import image from "/src/assets/categories/other.webp";\nglobalThis.__control = image;';
  },
};

let app: Emitted;
let control: Emitted;

describe("las imágenes de categoría en la compilación", () => {
  beforeAll(async () => {
    // La interfaz entera con su configuración real y el umbral de incrustación muy alto
    app = emittedOf(
      await build({
        root,
        configFile: `${root}vite.config.ts`,
        envDir: false,
        logLevel: "silent",
        mode: "production",
        build: { write: false, minify: false, assetsInlineLimit: HUGE_INLINE_LIMIT },
      }),
    );
    // El control: sin configuración, con una sola entrada que no lleva la guarda
    control = emittedOf(
      await build({
        root,
        configFile: false,
        envDir: false,
        publicDir: false,
        logLevel: "silent",
        mode: "production",
        plugins: [controlEntry],
        build: {
          write: false,
          minify: false,
          assetsInlineLimit: HUGE_INLINE_LIMIT,
          rolldownOptions: { input: CONTROL_ENTRY },
        },
      }),
    );
  }, 30_000);

  it("cada imagen de categoría sale como fichero emitido, aunque el umbral sea muy alto", () => {
    const emittedNames = assetsOf(app)
      .flatMap((asset) => asset.originalFileNames)
      .filter((name) => name.includes(CATEGORY_DIR))
      .map(fileNameOf)
      .sort();

    expect(emittedNames).toEqual(CATEGORY_KEYS.map((key) => `${key}.webp`).sort());
  });

  it("el JS hace referencia a cada fichero emitido de una imagen de categoría", () => {
    const files = assetsOf(app)
      .filter((asset) => asset.originalFileNames.some((name) => name.includes(CATEGORY_DIR)))
      .map((asset) => asset.fileName);
    const code = chunksOf(app)
      .map((chunk) => chunk.code)
      .join("\n");

    expect(files).toHaveLength(CATEGORY_KEYS.length);
    for (const file of files) expect(code).toContain(file);
  });

  it("ninguna WebP queda incrustada como data: en el JS ni en el CSS", () => {
    const js = chunksOf(app).map((chunk) => chunk.code);
    const css = assetsOf(app)
      .filter((asset) => asset.fileName.endsWith(".css"))
      .map((asset) => textOf(asset.source));

    expect([...js, ...css].filter((text) => text.includes("data:image/webp"))).toEqual([]);
  });

  it("una imagen importada sin la guarda sí se incrusta con el mismo umbral (control)", () => {
    const code = chunksOf(control)
      .map((chunk) => chunk.code)
      .join("\n");

    expect(code).toContain("data:image/webp");
    expect(assetsOf(control).filter((asset) => asset.fileName.endsWith(".webp"))).toEqual([]);
  });
});
