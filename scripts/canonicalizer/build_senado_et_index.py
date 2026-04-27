"""Build the Senado ET pr-segment article index.

The Estatuto Tributario on `secretariasenado.gov.co` is split across
~36 segment files (`estatuto_tributario_pr001.html` ..
`estatuto_tributario_pr035.html`). The article-number → segment mapping
is NOT a clean numeric formula, so we sweep the segments once and write
the resulting article → segment lookup to
`var/senado_et_pr_index.json`. The Senado scraper reads this file at
import time.

Run when:
  * The cache is empty / index is missing.
  * Senado adds new segments (rare; ET reforms rebucket articles).
  * You suspect the index is stale (sub-units missing for a recent reform).

Usage:
  PYTHONPATH=src:. uv run python scripts/canonicalizer/build_senado_et_index.py

Output: `var/senado_et_pr_index.json` — a JSON object mapping article
identifiers ("555", "555-2", "689-3", ...) to zero-padded 3-digit segment
ids ("023", "028", ...).

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

LOGGER = logging.getLogger("build_senado_et_index")

BASE = "http://www.secretariasenado.gov.co/senado/basedoc"
DEFAULT_INDEX_PATH = Path("var/senado_et_pr_index.json")
DEFAULT_MAX_PR = 130
DEFAULT_STOP_AFTER_404 = 5

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "Lia-Graph/1.0 (compliance index builder)"
)

RX_ART = re.compile(r"ART[ÍI]CULO[^A-Za-z0-9]*([0-9]+(?:-[0-9]+)?)", re.IGNORECASE)


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
        url = f"{BASE}/estatuto_tributario_pr{seg}.html"
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
                content = resp.read().decode("utf-8", errors="ignore")
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
        arts = sorted(
            set(RX_ART.findall(content)),
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
