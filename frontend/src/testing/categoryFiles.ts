export type CategoryFileProblems = { missing: string[]; extra: string[] };

// Los nombres son relativos a la carpeta y se comparan distinguiendo mayúsculas
export function categoryFileProblems(names: readonly string[], keys: readonly string[]): CategoryFileProblems {
  const present = new Set(names);
  const expected = new Set(keys.map((key) => `${key}.webp`));
  return {
    missing: keys.filter((key) => !present.has(`${key}.webp`)),
    extra: names.filter((name) => !expected.has(name)),
  };
}
