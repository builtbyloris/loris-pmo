import { afterEach, describe, expect, it, vi } from "vitest";

import { apiUrl } from "./api";
import { normalizeApiBase } from "./api-base";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("API base URL", () => {
  it("keeps same-origin paths when no base URL is configured", () => {
    expect(apiUrl("/api/v1/projects")).toBe("/api/v1/projects");
  });

  it("preserves absolute backend-provided URLs", () => {
    expect(apiUrl("https://api.example.test/oauth")).toBe(
      "https://api.example.test/oauth",
    );
  });

  it("rejects ambiguous relative paths", () => {
    expect(() => apiUrl("api/v1/projects")).toThrow(
      "API paths must be absolute application paths.",
    );
  });

  it.each([undefined, ""])("treats %s as intentional same-origin", async (base) => {
    vi.stubEnv("VITE_API_BASE_URL", base);
    vi.resetModules();
    const configured = await import("./api");
    expect(configured.apiUrl("/api/v1/projects")).toBe("/api/v1/projects");
  });

  it("uses the HTTPS backend origin including OAuth endpoints", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");
    vi.resetModules();
    const configured = await import("./api");
    expect(configured.apiUrl("/api/v1/projects")).toBe("https://api.example.test/api/v1/projects");
    expect(configured.apiUrl("/api/v1/integrations/oauth/google/callback")).toBe(
      "https://api.example.test/api/v1/integrations/oauth/google/callback",
    );
  });

  it.each(["not-an-origin", "ftp://api.example.test", "https://api.example.test/path", "https://user:pass@api.example.test", "https://api.example.test?token=value", "https://*.example.test"])(
    "rejects invalid base %s with the shared build/runtime validator", (base) => {
      expect(() => normalizeApiBase(base, true)).toThrow("VITE_API_BASE_URL");
    },
  );

  it("requires HTTPS only for nonempty production origins", () => {
    expect(() => normalizeApiBase("http://api.example.test", true)).toThrow("HTTPS");
    expect(normalizeApiBase("http://localhost:8000", false)).toBe("http://localhost:8000");
    expect(normalizeApiBase("", true)).toBe("");
    expect(normalizeApiBase("https://api.example.test/", true)).toBe("https://api.example.test");
  });
});
