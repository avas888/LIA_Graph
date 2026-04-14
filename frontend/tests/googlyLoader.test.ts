import { beforeEach, describe, expect, it } from "vitest";
import { createGooglyLoader } from "@/shared/ui/googlyLoader";

describe("googlyLoader", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("creates a loader element with role=status", () => {
    const loader = createGooglyLoader("Cargando...");
    expect(loader.el).toBeInstanceOf(HTMLElement);
    expect(loader.el.getAttribute("role")).toBe("status");
    expect(loader.el.getAttribute("aria-live")).toBe("polite");
    expect(loader.el.classList.contains("googly-loader")).toBe(true);
  });

  it("renders the label text", () => {
    const loader = createGooglyLoader("Cargando historial...");
    const label = loader.el.querySelector(".googly-loader-label");
    expect(label).not.toBeNull();
    expect(label?.textContent).toBe("Cargando historial...");
  });

  it("renders the googly eye structure", () => {
    const loader = createGooglyLoader();
    const orb = loader.el.querySelector(".googly-loader-orb");
    expect(orb).not.toBeNull();
    const eyes = loader.el.querySelectorAll(".lia-thinking-eye");
    expect(eyes).toHaveLength(2);
    const pupils = loader.el.querySelectorAll(".lia-thinking-eye-pupil");
    expect(pupils).toHaveLength(2);
  });

  it("show/hide toggle the hidden attribute", () => {
    const loader = createGooglyLoader("test");
    expect(loader.el.hidden).toBe(false);

    loader.hide();
    expect(loader.el.hidden).toBe(true);

    loader.show();
    expect(loader.el.hidden).toBe(false);
  });

  it("setText updates the label", () => {
    const loader = createGooglyLoader("initial");
    loader.setText("updated");
    const label = loader.el.querySelector(".googly-loader-label");
    expect(label?.textContent).toBe("updated");
  });

  it("setText creates label if none existed", () => {
    const loader = createGooglyLoader(); // no label
    expect(loader.el.querySelector(".googly-loader-label")).toBeNull();
    loader.setText("new label");
    const label = loader.el.querySelector(".googly-loader-label");
    expect(label).not.toBeNull();
    expect(label?.textContent).toBe("new label");
  });

  it("remove detaches from DOM", () => {
    const loader = createGooglyLoader("test");
    document.body.appendChild(loader.el);
    expect(document.querySelector(".googly-loader")).not.toBeNull();

    loader.remove();
    expect(document.querySelector(".googly-loader")).toBeNull();
  });
});
