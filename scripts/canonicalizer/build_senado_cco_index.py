"""Build the Senado Código de Comercio (CCo) pr-segment article index.

The Código de Comercio on `secretariasenado.gov.co` is split across
~30 segment files (`codigo_comercio_pr001.html` .. `codigo_comercio_pr029.html`).
The article-number → segment mapping is NOT a clean numeric formula,
so we sweep the segments once and write the resulting article →
segment lookup to ``var/senado_cco_pr_index.json``.

The Senado scraper reads this file at import time so per-article
fetches resolve to the right segment URL — the master `codigo_comercio.html`
page is too long to slice reliably, but each pr-segment is small.

Mirror of `scripts/canonicalizer/build_senado_et_index.py` (next_v7
§3.4 step 3b — closes the K3 CCo gap).

Run when:
  * The cache is empty / index is missing.
  * Senado adds new segments (rare; CCo reforms rebucket articles).
  * You suspect the index is stale (sub-units missing for a recent reform).

Usage:
  PYTHONPATH=src:. uv run python scripts/canonicalizer/build_senado_cco_index.py

Output: ``var/senado_cco_pr_index.json`` — a JSON object mapping
article identifiers ("1", "98", "1234", "1234-1", ...) to zero-padded
3-digit segment ids ("001", "012", ...).

See `docs/learnings/sites/secretariasenado.md` for why this is necessary.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LOGGER = logging.getLogger("build_senado_cco_index")

BASE = "http://www.secretariasenado.gov.co/senado/basedoc"
DEFAULT_INDEX_PATH = Path("var/senado_cco_pr_index.json")
DEFAULT_MAX_PR = 100
DEFAULT_STOP_AFTER_404 = 5

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "Lia-Graph/1.0 (compliance index builder)"
)

# The CCo Senado pages serve ISO-8859-1 with HTML-entity accents
# (`ART&Iacute;CULO`) and rely on `<A name="<num>">` anchors as the
# canonical per-article landmark. Extract directly from the anchors —
# more reliable than parsing the heading text whose accent encoding
# changes across older / newer pr-segments.
RX_ART_ANCHOR = re.compile(r'<[Aa]\s+name="(\d+(?:-\d+)?)"', re.IGNORECASE)
# Fallback for pages that lack anchors but include the heading text.
RX_ART_TEXT = re.compile(
    r"ART(?:[ÍI]|&Iacute;|&iacute;)CULO[^A-Za-z0-9]*([0-9]+(?:-[0-9]+)?)",
    re.IGNORECASE,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output", default=str(DEFAULT_INDEX_PATH))
    p.add_argument("--max-pr", type=int, default=DEFAULT_MAX_PR,
                   help="Highest pr-number to probe before giving up.")
    p.add_argument("--stop-after-404", type=int, default=DEFAULT_STOP_AFTER_404,
                   help="Stop after this many consecutive 404s.")
    p.add_argument("--rate-limit", type=float, default=0.5,
                   help="Seconds between requests (Senado is polite about 0.5).")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    mapping: dict[str, str] = {}
    consec_404 = 0
    pages_seen = 0

    for pr in range(0, args.max_pr):
        seg = f"{pr:03d}"
        url = f"{BASE}/codigo_comercio_pr{seg}.html"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    consec_404 += 1
                    LOGGER.info("pr%s HTTP %d", seg, resp.status)
                    if consec_404 >= args.stop_after_404:
                        LOGGER.info("Stopping: %d consecutive non-200s.", consec_404)
                        break
                    continue
                # Senado serves CCo pages as ISO-8859-1; UTF-8 decode
                # mangles accented headings.
                content = resp.read().decode("iso-8859-1", errors="ignore")
        except urllib.error.HTTPError as err:
            if err.code == 404:
                consec_404 += 1
                LOGGER.info("pr%s 404", seg)
                if consec_404 >= args.stop_after_404:
                    LOGGER.info("Stopping: %d consecutive 404s.", consec_404)
                    break
                continue
            LOGGER.warning("pr%s HTTPError %d", seg, err.code)
            continue
        except Exception as err:
            LOGGER.warning("pr%s failed: %s", seg, err)
            continue

        consec_404 = 0
        pages_seen += 1
        anchors = set(RX_ART_ANCHOR.findall(content))
        if anchors:
            raw_arts = anchors
        else:
            raw_arts = set(RX_ART_TEXT.findall(content))
        arts = sorted(
            raw_arts,
            key=lambda a: (int(a.split("-")[0]), int(a.split("-")[1]) if "-" in a else 0),
        )
        for art in arts:
            mapping.setdefault(art, seg)
        first = arts[0] if arts else "—"
        last = arts[-1] if arts else "—"
        LOGGER.info("pr%s ✓ %d articles (%s..%s)", seg, len(arts), first, last)
        time.sleep(args.rate_limit)

    output_path.write_text(json.dumps(mapping, indent=2, sort_keys=True), encoding="utf-8")
    LOGGER.info(
        "Wrote %s — %d articles indexed across %d segments.",
        output_path,
        len(mapping),
        pages_seen,
    )
    return 0 if mapping else 1


if __name__ == "__main__":
    sys.exit(main())
