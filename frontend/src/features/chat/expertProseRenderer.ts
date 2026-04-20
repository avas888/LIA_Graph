/**
 * Expert prose renderer — minimal markdown subset for per-expert detail tabs.
 *
 * The backend `_expert_extended_excerpt` extractor emits a controlled subset
 * of markdown: `### h4`, `#### h5`, `- bullets`, `**bold**` inline,
 * paragraphs separated by blank lines. This renderer handles exactly that
 * subset — no headings ≥h3, no nesting, no images, no autolinks, no tables.
 * Keeps the surface tiny so future corpus changes don't ripple unexpectedly.
 */

const HEADING_RE = /^(#{3,5})\s+(.+)$/;
const BULLET_RE = /^-\s+(.+)$/;
const TABLE_LINE_RE = /^\|.+\|$/;

interface ProseBlock {
  kind: "heading" | "bullets" | "paragraph" | "table";
  level?: number;
  text?: string;
  items?: string[];
  /** Table rows; row 0 is the header (separator row already stripped server-side). */
  rows?: string[][];
}

function splitTableRow(row: string): string[] {
  // Strip leading/trailing pipes, then split. `|a|b|c|` → ["a","b","c"].
  const trimmed = row.replace(/^\|/, "").replace(/\|$/, "");
  return trimmed.split("|").map((cell) => cell.trim());
}

/**
 * Split a markdown table line that may contain multiple rows concatenated
 * by whitespace (e.g. when an upstream stage collapsed `\n` to ` `, the
 * boundary `…|\n|…` becomes `…| |…`). Returns the recovered row array.
 *
 * Heuristic: only split when the candidate divides cleanly into segments
 * with the SAME column count as the first segment. That keeps genuine
 * empty cells (`| |`) from being mistaken for row boundaries — a real
 * empty cell wouldn't produce repeated, equal-length groups.
 */
function recoverFlattenedTableRows(line: string): string[] {
  const segments = line.split(/\|\s+\|/);
  if (segments.length < 2) return [line];
  const headerCells = segments[0].replace(/^\|/, "").split("|").length;
  if (headerCells < 2) return [line];
  const rows: string[] = [];
  for (let i = 0; i < segments.length; i += 1) {
    let segment = segments[i];
    if (i > 0) segment = `|${segment}`;
    if (i < segments.length - 1) segment = `${segment}|`;
    const cellCount = segment.replace(/^\|/, "").replace(/\|$/, "").split("|").length;
    if (cellCount !== headerCells) return [line];
    rows.push(segment.trim());
  }
  return rows;
}

function parseExpertProseBlocks(markdown: string): ProseBlock[] {
  const blocks: ProseBlock[] = [];
  let bulletBuf: string[] = [];
  let paragraphBuf: string[] = [];
  let tableBuf: string[] = [];

  const flushBullets = () => {
    if (bulletBuf.length === 0) return;
    blocks.push({ kind: "bullets", items: [...bulletBuf] });
    bulletBuf = [];
  };
  const flushParagraph = () => {
    if (paragraphBuf.length === 0) return;
    blocks.push({ kind: "paragraph", text: paragraphBuf.join(" ").trim() });
    paragraphBuf = [];
  };
  const flushTable = () => {
    if (tableBuf.length === 0) return;
    const rows = tableBuf.map(splitTableRow).filter((row) => row.length > 0);
    tableBuf = [];
    if (rows.length > 0) blocks.push({ kind: "table", rows });
  };
  const flushAll = () => {
    flushBullets();
    flushParagraph();
    flushTable();
  };

  for (const rawLine of markdown.split("\n")) {
    const line = rawLine.trim();
    if (!line) {
      flushAll();
      continue;
    }
    if (TABLE_LINE_RE.test(line)) {
      flushBullets();
      flushParagraph();
      for (const row of recoverFlattenedTableRows(line)) {
        tableBuf.push(row);
      }
      continue;
    }
    const heading = HEADING_RE.exec(line);
    if (heading) {
      flushAll();
      blocks.push({ kind: "heading", level: heading[1].length, text: heading[2].trim() });
      continue;
    }
    const bullet = BULLET_RE.exec(line);
    if (bullet) {
      flushParagraph();
      flushTable();
      bulletBuf.push(bullet[1].trim());
      continue;
    }
    flushBullets();
    flushTable();
    paragraphBuf.push(line);
  }
  flushAll();
  return blocks;
}

function appendInlineWithBold(target: HTMLElement, text: string): void {
  // Split on **...** preserving the delimiters so we can rebuild with <strong>.
  const segments = text.split(/(\*\*[^*\n]+\*\*)/g);
  for (const segment of segments) {
    if (!segment) continue;
    const boldMatch = /^\*\*([^*\n]+)\*\*$/.exec(segment);
    if (boldMatch) {
      const strong = document.createElement("strong");
      strong.textContent = boldMatch[1];
      target.appendChild(strong);
    } else {
      target.appendChild(document.createTextNode(segment));
    }
  }
}

function renderHeadingBlock(host: HTMLElement, block: ProseBlock): void {
  const level = block.level === 5 ? "h5" : "h4";
  const heading = document.createElement(level);
  heading.className = "expert-detail-tab-heading";
  appendInlineWithBold(heading, block.text || "");
  host.appendChild(heading);
}

function renderBulletsBlock(host: HTMLElement, block: ProseBlock): void {
  const ul = document.createElement("ul");
  ul.className = "expert-detail-tab-list";
  for (const item of block.items || []) {
    const li = document.createElement("li");
    appendInlineWithBold(li, item);
    ul.appendChild(li);
  }
  host.appendChild(ul);
}

function renderParagraphBlock(host: HTMLElement, block: ProseBlock): void {
  const p = document.createElement("p");
  p.className = "expert-detail-tab-paragraph";
  appendInlineWithBold(p, block.text || "");
  host.appendChild(p);
}

function renderTableBlock(host: HTMLElement, block: ProseBlock): void {
  const rows = block.rows || [];
  if (rows.length === 0) return;
  // Wrap in an overflow scroll container so wide tables stay usable in a
  // narrow modal without overflowing the page.
  const wrapper = document.createElement("div");
  wrapper.className = "expert-detail-tab-table-wrapper";
  const table = document.createElement("table");
  table.className = "expert-detail-tab-table";

  const [headerRow, ...bodyRows] = rows;
  const thead = document.createElement("thead");
  const headerTr = document.createElement("tr");
  for (const cell of headerRow) {
    const th = document.createElement("th");
    appendInlineWithBold(th, cell);
    headerTr.appendChild(th);
  }
  thead.appendChild(headerTr);
  table.appendChild(thead);

  if (bodyRows.length > 0) {
    const tbody = document.createElement("tbody");
    for (const row of bodyRows) {
      const tr = document.createElement("tr");
      for (const cell of row) {
        const td = document.createElement("td");
        appendInlineWithBold(td, cell);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody);
  }

  wrapper.appendChild(table);
  host.appendChild(wrapper);
}

export function renderExpertProse(host: HTMLElement, markdown: string): void {
  host.replaceChildren();
  const blocks = parseExpertProseBlocks(markdown);
  for (const block of blocks) {
    if (block.kind === "heading") renderHeadingBlock(host, block);
    else if (block.kind === "bullets") renderBulletsBlock(host, block);
    else if (block.kind === "table") renderTableBlock(host, block);
    else renderParagraphBlock(host, block);
  }
}
