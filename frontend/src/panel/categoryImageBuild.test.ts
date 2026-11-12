import { build, type Plugin } from "vite";
import { beforeAll, describe, expect, it } from "vitest";

// Raíz del frontend; no hay tipos de Node, así que no se usa process ni node:path
const root = decodeURIComponent(new URL("../..", import.meta.url).pathname);
// Umbral de incrustación muy por encima del peso de cualquier imagen
const HUGE_INLINE_LIMIT = 1_000_000;
const CONTROL_ENTRY = "virtual:category-image-control";

// Las claves salen del mismo directorio que lee categoryImage.ts, sin cargar los ficheros
const categoryFiles = import.meta.glob("../assets/categories/*.svg", { query: "?url", import: "default" });

function slugOf(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1, path.lastIndexOf("."));
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
    return 'import image from "/src/assets/categories/other.svg";\nglobalThis.__control = image;';
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
    const emittedSlugs = assetsOf(app)
      .flatMap((asset) => asset.originalFileNames)
      .filter((name) => name.includes("/assets/categories/"))
      .map(slugOf)
      .sort();

    expect(emittedSlugs).toEqual(Object.keys(categoryFiles).map(slugOf).sort());
  });

  it("el JS hace referencia a cada fichero emitido de una imagen de categoría", () => {
    const files = assetsOf(app)
      .filter((asset) => asset.originalFileNames.some((name) => name.includes("/assets/categories/")))
      .map((asset) => asset.fileName);
    const code = chunksOf(app)
      .map((chunk) => chunk.code)
      .join("\n");

    expect(files.length).toBeGreaterThan(0);
    for (const file of files) expect(code).toContain(file);
  });

  it("una imagen importada sin la guarda sí se incrusta con el mismo umbral (control)", () => {
    const code = chunksOf(control)
      .map((chunk) => chunk.code)
      .join("\n");

    expect(code).toContain("data:image/svg+xml");
    expect(assetsOf(control).filter((asset) => asset.fileName.endsWith(".svg"))).toEqual([]);
  });
});
