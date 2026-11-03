// ?no-inline hace que salgan como ficheros y no como data:, para poder cerrar img-src a 'self'
const files = import.meta.glob<string>("../assets/categories/*.svg", {
  eager: true,
  query: "?no-inline",
  import: "default",
});

function slugOf(path: string): string {
  return path.slice(path.lastIndexOf("/") + 1, -".svg".length);
}

// Un Map y no un objeto: un slug como __proto__ o constructor no debe devolver nada heredado
const imageBySlug = new Map(Object.entries(files).map(([path, url]) => [slugOf(path), url]));

const otherImage = imageBySlug.get("other");
if (otherImage === undefined) throw new Error("Falta la imagen de la categoría other");
const fallback: string = otherImage;

export function categoryImage(slug: string): string {
  return imageBySlug.get(slug) ?? fallback;
}
