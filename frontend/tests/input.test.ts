import { describe, expect, it } from "vitest";
import { createInput, createTextarea } from "@/shared/ui/atoms/input";

describe("createInput", () => {
  it("creates an input with default options", () => {
    const el = createInput({});
    expect(el.tagName).toBe("INPUT");
    expect(el.type).toBe("text");
    expect(el.className).toBe("lia-input");
    expect(el.getAttribute("data-lia-component")).toBe("input");
    expect(el.disabled).toBe(false);
    expect(el.required).toBe(false);
  });

  it("applies all scalar options", () => {
    const el = createInput({
      type: "email",
      className: "custom",
      id: "my-id",
      name: "email",
      placeholder: "Enter email",
      value: "a@b.com",
      required: true,
      disabled: true,
      autocomplete: "email",
      minlength: 3,
      maxlength: 50,
      dataComponent: "email-input",
    });
    expect(el.type).toBe("email");
    expect(el.className).toBe("lia-input custom");
    expect(el.id).toBe("my-id");
    expect(el.name).toBe("email");
    expect(el.placeholder).toBe("Enter email");
    expect(el.value).toBe("a@b.com");
    expect(el.required).toBe(true);
    expect(el.disabled).toBe(true);
    expect(el.autocomplete).toBe("email");
    expect(el.minLength).toBe(3);
    expect(el.maxLength).toBe(50);
    expect(el.getAttribute("data-lia-component")).toBe("email-input");
  });

  it("applies extra attrs", () => {
    const el = createInput({ attrs: { "aria-label": "Search", "data-test": "1" } });
    expect(el.getAttribute("aria-label")).toBe("Search");
    expect(el.getAttribute("data-test")).toBe("1");
  });

  it("omits optional attributes when not provided", () => {
    const el = createInput({});
    expect(el.id).toBe("");
    expect(el.name).toBe("");
    expect(el.placeholder).toBe("");
    expect(el.value).toBe("");
  });
});

describe("createTextarea", () => {
  it("creates a textarea with default options", () => {
    const el = createTextarea({});
    expect(el.tagName).toBe("TEXTAREA");
    expect(el.className).toBe("lia-input lia-textarea");
    expect(el.getAttribute("data-lia-component")).toBe("textarea");
    expect(el.rows).toBe(3);
    expect(el.disabled).toBe(false);
    expect(el.required).toBe(false);
  });

  it("applies all scalar options", () => {
    const el = createTextarea({
      className: "wide",
      id: "notes",
      name: "notes",
      placeholder: "Type here",
      value: "hello",
      required: true,
      disabled: true,
      rows: 8,
      maxlength: 500,
      dataComponent: "note-area",
    });
    expect(el.className).toBe("lia-input lia-textarea wide");
    expect(el.id).toBe("notes");
    expect(el.name).toBe("notes");
    expect(el.placeholder).toBe("Type here");
    expect(el.value).toBe("hello");
    expect(el.required).toBe(true);
    expect(el.disabled).toBe(true);
    expect(el.rows).toBe(8);
    expect(el.maxLength).toBe(500);
    expect(el.getAttribute("data-lia-component")).toBe("note-area");
  });

  it("applies extra attrs", () => {
    const el = createTextarea({ attrs: { "aria-describedby": "hint" } });
    expect(el.getAttribute("aria-describedby")).toBe("hint");
  });
});
