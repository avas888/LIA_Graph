import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LiaThinkingAnimation } from "@/shared/async/liaThinkingAnimation";

function createContainer(): HTMLDivElement {
  const el = document.createElement("div");
  el.id = "test-poses";
  document.body.appendChild(el);
  return el;
}

function mockMatchMedia(reducedMotion: boolean = false) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: reducedMotion && query === "(prefers-reduced-motion: reduce)",
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

describe("LiaThinkingAnimation", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    vi.useFakeTimers();
    mockMatchMedia(false);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("throws if container not found", () => {
    expect(() => new LiaThinkingAnimation("nonexistent")).toThrow(
      "Container #nonexistent not found",
    );
  });

  it("creates img elements on init", () => {
    createContainer();
    const anim = new LiaThinkingAnimation("test-poses");
    anim.init();

    const images = document.querySelectorAll(".lia-pose");
    expect(images).toHaveLength(10);
  });

  it("marks exactly one pose as active after init", () => {
    createContainer();
    const anim = new LiaThinkingAnimation("test-poses");
    anim.init();

    const active = document.querySelectorAll(".lia-pose.active");
    expect(active).toHaveLength(1);
  });

  it("adds lia-thinking-container class on init", () => {
    const el = createContainer();
    const anim = new LiaThinkingAnimation("test-poses");
    anim.init();

    expect(el.classList.contains("lia-thinking-container")).toBe(true);
  });

  it("cycles to a different pose on interval tick", () => {
    createContainer();
    const anim = new LiaThinkingAnimation("test-poses", 1000);
    anim.init();

    const getActiveIndex = () => {
      const imgs = document.querySelectorAll(".lia-pose");
      for (let i = 0; i < imgs.length; i++) {
        if (imgs[i].classList.contains("active")) return i;
      }
      return -1;
    };

    const initialIndex = getActiveIndex();
    anim.start();
    vi.advanceTimersByTime(1000);

    const newIndex = getActiveIndex();
    expect(newIndex).not.toBe(initialIndex);
    expect(document.querySelectorAll(".lia-pose.active")).toHaveLength(1);

    anim.stop();
  });

  it("stop() halts cycling", () => {
    createContainer();
    const anim = new LiaThinkingAnimation("test-poses", 500);
    anim.init();

    anim.start();
    vi.advanceTimersByTime(500);
    anim.stop();

    const activeAfterStop = document.querySelectorAll(".lia-pose.active");
    const countBefore = activeAfterStop.length;

    vi.advanceTimersByTime(2000);
    const countAfter = document.querySelectorAll(".lia-pose.active").length;
    expect(countAfter).toBe(countBefore);
  });

  it("does not start cycling when prefers-reduced-motion is set", () => {
    mockMatchMedia(true);

    createContainer();
    const anim = new LiaThinkingAnimation("test-poses", 500);
    anim.init();

    const getActiveIndex = () => {
      const imgs = document.querySelectorAll(".lia-pose");
      for (let i = 0; i < imgs.length; i++) {
        if (imgs[i].classList.contains("active")) return i;
      }
      return -1;
    };

    const initial = getActiveIndex();
    anim.start();
    vi.advanceTimersByTime(2000);

    expect(getActiveIndex()).toBe(initial);
  });
});
