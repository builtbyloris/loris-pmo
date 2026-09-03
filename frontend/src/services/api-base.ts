/** Empty/unset means same-origin; nonempty values must be explicit origins. */
export function normalizeApiBase(value: string | undefined, production: boolean): string {
  const base = (value ?? "").trim();
  if (!base) return "";
  let parsed: URL;
  try {
    parsed = new URL(base);
  } catch {
    throw new Error("VITE_API_BASE_URL must be a valid HTTP(S) origin.");
  }
  if (
    !["http:", "https:"].includes(parsed.protocol) ||
    !parsed.hostname || parsed.hostname.includes("*") ||
    parsed.username || parsed.password || parsed.search || parsed.hash ||
    (parsed.pathname !== "" && parsed.pathname !== "/")
  ) {
    throw new Error("VITE_API_BASE_URL must be a valid HTTP(S) origin.");
  }
  if (production && parsed.protocol !== "https:") {
    throw new Error("VITE_API_BASE_URL must use HTTPS for production builds.");
  }
  return parsed.origin;
}
