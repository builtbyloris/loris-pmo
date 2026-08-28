export function formatCurrency(value: string | number, language = "en"): string {
  return new Intl.NumberFormat(language, {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function formatDate(value: string | null, language = "en"): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(language, { dateStyle: "medium", timeZone: "UTC" }).format(
    new Date(`${value}T00:00:00Z`),
  );
}
