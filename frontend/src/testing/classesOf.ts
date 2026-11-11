export const classesOf = (tag: string) => (tag.match(/class="([^"]*)"/)?.[1] ?? "").split(" ");
