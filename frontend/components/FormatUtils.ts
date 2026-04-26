function normalizeToRows(data: unknown): Record<string, unknown>[] {
  if (!data) return [];
  if (Array.isArray(data))
    return data.length && typeof data[0] === "object"
      ? data
      : data.map((v, i) => ({ index: i, value: v }));
      
  if (typeof data === "object") {
    const arrKey = Object.keys(data as object).find((k) =>
      Array.isArray((data as Record<string, unknown>)[k]),
    );
    if (arrKey)
      return normalizeToRows((data as Record<string, unknown>)[arrKey]);
    return [data as Record<string, unknown>];
  }
  return [{ value: data }];
}

export function formatData(data: unknown): string {
  const rows = normalizeToRows(data);
  return JSON.stringify(rows, null, 2);
}
