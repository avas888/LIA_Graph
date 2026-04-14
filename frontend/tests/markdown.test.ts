import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderMarkdown } from "@/content/markdown";

describe("renderMarkdown", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", vi.fn().mockReturnValue({ matches: false }));
  });

  it("renders sanitized markdown with safe anchors", async () => {
    const container = document.createElement("div");
    const scrollContainer = document.createElement("div");
    scrollContainer.appendChild(container);

    await renderMarkdown(container, "**Hola** [mundo](/norma)", {
      scrollContainer,
    });

    expect(container.querySelector("strong")?.textContent).toBe("Hola");
    expect(container.querySelector("a")?.getAttribute("href")).toBe("/norma");
  });

  it("renders content with atomic blocks instantly", async () => {
    const container = document.createElement("div");
    const scrollContainer = document.createElement("div");
    scrollContainer.appendChild(container);

    await renderMarkdown(
      container,
      "Texto inicial\n\n```js\nconst value = 1;\n```",
      {
        scrollContainer,
      }
    );

    expect(container.textContent).toContain("Texto inicial");
    expect(container.querySelector("pre")?.textContent).toContain("const value = 1;");
  });

  it("preserves list structure and formatting", async () => {
    const container = document.createElement("div");
    const scrollContainer = document.createElement("div");
    scrollContainer.appendChild(container);

    await renderMarkdown(
      container,
      "* **Primer paso:** Texto inicial\n* **Segundo paso:** Seguimiento\n\n```js\nconst total = 2;\n```\n\n* Tercer paso",
      {
        scrollContainer,
      }
    );

    expect(container.querySelectorAll("ul li")).toHaveLength(3);
    expect(container.querySelector("strong")).not.toBeNull();
    expect(container.querySelector("pre")?.textContent).toContain("const total = 2;");
    expect(container.textContent).toContain("Primer paso:");
    expect(container.textContent).toContain("Tercer paso");
  });
});
