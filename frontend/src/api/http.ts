const JSON_CONTENT_TYPE = /^application\/json\s*(;|$)/i;

export function hasJsonContentType(response: Response): boolean {
  return JSON_CONTENT_TYPE.test(response.headers.get("Content-Type")?.trim() ?? "");
}
