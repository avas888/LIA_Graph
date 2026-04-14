import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { isMobile } from "@/app/mobile/detectMobile";

describe("isMobile", () => {
  const originalUA = navigator.userAgent;

  beforeEach(() => {
    // Default: desktop UA, wide viewport
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true, configurable: true });
  });

  afterEach(() => {
    Object.defineProperty(navigator, "userAgent", { value: originalUA, writable: true, configurable: true });
  });

  it("returns false for desktop user-agent and wide viewport", () => {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window, "innerWidth", { value: 1024, writable: true, configurable: true });
    expect(isMobile()).toBe(false);
  });

  it("returns true for iPhone user-agent", () => {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
      writable: true,
      configurable: true,
    });
    expect(isMobile()).toBe(true);
  });

  it("returns true for Android user-agent", () => {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (Linux; Android 13; Pixel 7)",
      writable: true,
      configurable: true,
    });
    expect(isMobile()).toBe(true);
  });

  it("returns true for narrow viewport even with desktop UA", () => {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window, "innerWidth", { value: 500, writable: true, configurable: true });
    expect(isMobile()).toBe(true);
  });

  it("returns false for viewport at exactly 768", () => {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window, "innerWidth", { value: 768, writable: true, configurable: true });
    expect(isMobile()).toBe(false);
  });

  it("returns true for iPad user-agent", () => {
    Object.defineProperty(navigator, "userAgent", {
      value: "Mozilla/5.0 (iPad; CPU OS 16_0 like Mac OS X)",
      writable: true,
      configurable: true,
    });
    expect(isMobile()).toBe(true);
  });
});
