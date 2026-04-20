/**
 * @vitest-environment jsdom
 */
import { describe, expect, it } from "vitest";

import { buildLinkableListNode } from "@/shared/ui/molecules/linkableList";

describe("buildLinkableListNode", () => {
  it("returns null when items is empty or not an array", () => {
    expect(buildLinkableListNode(null)).toBeNull();
    expect(buildLinkableListNode([])).toBeNull();
    // @ts-expect-error defensive check on bad input
    expect(buildLinkableListNode("nope")).toBeNull();
  });

  it("renders anchor for items with a valid href", () => {
    const ul = buildLinkableListNode(
      [
        { text: "Oficio DIAN 635 de 2019", href: "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_0635_2019.htm#INICIO" },
      ],
      { className: "norma-annot-list" },
    )!;
    expect(ul).toBeTruthy();
    expect(ul.className).toBe("norma-annot-list");
    const li = ul.querySelector("li")!;
    const a = li.querySelector("a")!;
    expect(a).toBeTruthy();
    expect(a.getAttribute("href")).toBe(
      "https://normograma.dian.gov.co/dian/compilacion/docs/oficio_dian_0635_2019.htm#INICIO",
    );
    expect(a.getAttribute("target")).toBe("_blank");
    expect(a.getAttribute("rel")).toBe("noopener noreferrer");
    expect(a.textContent).toBe("Oficio DIAN 635 de 2019");
  });

  it("renders plain text li when href is missing or unsafe", () => {
    const ul = buildLinkableListNode([
      { text: "Corte Constitucional — Sentencia C-087-19" },
      { text: "Javascript nope", href: "javascript:alert(1)" },
      { text: "Empty href", href: "" },
    ])!;
    expect(ul).toBeTruthy();
    const lis = ul.querySelectorAll("li");
    expect(lis).toHaveLength(3);
    for (const li of Array.from(lis)) {
      expect(li.querySelector("a")).toBeNull();
    }
    expect(lis[1].textContent).toBe("Javascript nope");
  });

  it("mixes anchors and plain text in source order", () => {
    const ul = buildLinkableListNode([
      { text: "Linked", href: "https://example.com/a" },
      { text: "Bare text" },
      { text: "Linked 2", href: "https://example.com/b" },
    ])!;
    const lis = ul.querySelectorAll("li");
    expect(lis[0].querySelector("a")?.getAttribute("href")).toBe("https://example.com/a");
    expect(lis[1].querySelector("a")).toBeNull();
    expect(lis[2].querySelector("a")?.getAttribute("href")).toBe("https://example.com/b");
  });

  it("falls back to href as anchor text when text is missing", () => {
    const ul = buildLinkableListNode([
      { href: "https://example.com/lonely" },
    ])!;
    const a = ul.querySelector("a")!;
    expect(a.textContent).toBe("https://example.com/lonely");
  });
});
