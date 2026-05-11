"""URL transforms for Colombian normativa hosts.

The citation-profile "Ir a documento original" action and a few other
user-facing surfaces need to rewrite corpus URLs into hosts whose pages
actually scroll correctly when opened. This module owns those rewrites.

Two distinct concerns live here:

  * `_prefer_normograma_mintic_mirror` — DIAN's Normograma compilation pages
    do not honor article fragment anchors like `#807`. MinTIC mirrors the
    same content at the same paths and does honor them, so we swap DIAN
    URLs to MinTIC for user-clickable links. Has been the canonical link
    target for ET citations.

  * `_prefer_secretariasenado_for_et` — Secretaría del Senado serves the
    ET as ~37 small per-section files (~50–300 KB each) instead of MinTIC's
    3.35 MB monolith, eliminating the anchor-scroll race that occasionally
    drops MinTIC users at the top of the page on first click. Backed by
    `config/et_senado_section_map.json` (article number → three-digit
    section identifier). Falls back silently when the article isn't in the
    map, so MinTIC stays as the safety net.

Both helpers were extracted from `ui_text_utilities.py` once that file
crossed 1000 LOC; `ui_text_utilities` re-exports them for back-compat.
"""

from __future__ import annotations

import json
from pathlib import Path

_NORMOGRAMA_DIAN_BASE = "https://normograma.dian.gov.co/dian/compilacion/docs"
_NORMOGRAMA_MINTIC_BASE = "https://normograma.mintic.gov.co/mintic/compilacion/docs"


# ---------------------------------------------------------------------------
# Normograma DIAN → MinTIC mirror swap
# ---------------------------------------------------------------------------
#
# The DIAN Normograma compilation pages (e.g. `estatuto_tributario.htm`) are
# served from two canonical hosts with identical paths and content:
#
#   DIAN:    https://normograma.dian.gov.co/dian/compilacion/docs/...
#   MinTIC:  https://normograma.mintic.gov.co/mintic/compilacion/docs/...
#
# The ET article corpus stores DIAN URLs with fragment anchors like
# `estatuto_tributario.htm#807`, but the DIAN host does not reliably honor
# those fragments — clicking the link lands the user at the top of the page.
# The MinTIC mirror does honor them, so we prefer MinTIC for user-facing
# "Ir a documento original" actions.
#
# Known breakage (as of 2026-04-05): MinTIC's Let's Encrypt cert for
# `normograma.mintic.gov.co` expired on Apr 5 19:54:55 2026 GMT because
# auto-renewal failed on their side. Users must accept the expired-cert
# browser warning once; afterwards all MinTIC URLs work normally. We
# prefer MinTIC everywhere (backend + frontend) because DIAN does not
# honor fragment anchors (#807 etc.) while MinTIC does. The canonical
# DIAN→MinTIC swap also lives in `contracts/advisory.py` for the Citation
# model output path.
#
# Re-check cert validity before assuming this is still broken:
#   echo | openssl s_client -servername normograma.mintic.gov.co \
#     -connect normograma.mintic.gov.co:443 2>/dev/null \
#     | openssl x509 -noout -dates
#
# This helper was historically mirrored by the frontend helper
# `normogramaMirrorUrl` in `frontend/src/features/chat/citations.ts`, but
# that UI was retired in a7031e6e and its fallback URL no longer reaches a
# user-visible rendering surface today. The single source of truth for the
# user-clickable MinTIC URL is now this backend helper.


def _prefer_normograma_mintic_mirror(url: str | None) -> str:
    """Swap a DIAN Normograma URL for its MinTIC mirror equivalent.

    Returns the input unchanged for non-Normograma URLs, URLs already on
    the MinTIC host, empty strings, or None. Fragment anchors (and any
    query string) are preserved so `#807` stays intact.

    This is used by the citation-profile "Ir a documento original" action
    because DIAN's compilation pages do not honor article fragments
    reliably, while MinTIC's mirror does.
    """
    if not url:
        return ""
    s = str(url).strip()
    if not s:
        return ""
    if s.startswith(_NORMOGRAMA_DIAN_BASE):
        return _NORMOGRAMA_MINTIC_BASE + s[len(_NORMOGRAMA_DIAN_BASE):]
    return s


# ---------------------------------------------------------------------------
# Secretaría del Senado per-section ET URLs
# ---------------------------------------------------------------------------
#
# Senado serves the Estatuto Tributario as ~37 small section files
# (estatuto_tributario.html for arts 1–21, then estatuto_tributario_pr001.html
# through estatuto_tributario_pr036.html) instead of the 3.35 MB monolith
# MinTIC hosts. The small files eliminate the anchor-scroll race that
# sometimes lands MinTIC users at the top of the page on first click.
#
# HTTP-only on purpose: port 443 is not listening on
# www.secretariasenado.gov.co as of 2026-05-10. An https:// URL would hand
# the user a connect-timeout. Re-check with `python3 -c "import socket;
# s=socket.socket(); s.settimeout(5); s.connect(('www.secretariasenado.gov.co',443))"`
# before flipping to https://.
#
# Anchor convention is identical to MinTIC (`<a class="bookmarkaj" name="107">…</a>`),
# so the fragment from the corpus URL is preserved verbatim.
_SECRETARIASENADO_ET_BASE = "http://www.secretariasenado.gov.co/senado/basedoc"
_ET_SENADO_SECTION_MAP: dict[str, str] | None = None
_ET_NORMOGRAMA_HOSTS: tuple[str, ...] = (
    _NORMOGRAMA_DIAN_BASE + "/estatuto_tributario.htm",
    _NORMOGRAMA_MINTIC_BASE + "/estatuto_tributario.htm",
)


def _load_et_senado_section_map() -> dict[str, str]:
    """Load article-number -> three-digit section identifier mapping for
    Secretaría del Senado's ET. Empty-string value means the article lives
    on the landing page (estatuto_tributario.html). Caches after first read."""
    global _ET_SENADO_SECTION_MAP
    if _ET_SENADO_SECTION_MAP is not None:
        return _ET_SENADO_SECTION_MAP
    cfg_path = Path(__file__).resolve().parents[2] / "config" / "et_senado_section_map.json"
    if cfg_path.exists():
        try:
            raw = json.loads(cfg_path.read_text(encoding="utf-8"))
            _ET_SENADO_SECTION_MAP = {
                str(k): str(v) for k, v in raw.items() if not str(k).startswith("_")
            }
        except Exception:
            _ET_SENADO_SECTION_MAP = {}
    else:
        _ET_SENADO_SECTION_MAP = {}
    return _ET_SENADO_SECTION_MAP


def _prefer_secretariasenado_for_et(url: str | None) -> str:
    """Swap a DIAN/MinTIC Estatuto Tributario compilation URL for its
    Secretaría del Senado per-section equivalent when the article is in
    config/et_senado_section_map.json.

    Returns the input unchanged when the URL is not an ET compilation URL,
    when the URL has no fragment, or when the article is not in the map
    (so the caller can fall back to the MinTIC mirror).
    """
    if not url:
        return ""
    s = str(url).strip()
    if not s or "#" not in s:
        return s
    base, _, fragment = s.partition("#")
    article = fragment.strip()
    if not article:
        return s
    if not any(base == host for host in _ET_NORMOGRAMA_HOSTS):
        return s
    section = _load_et_senado_section_map().get(article)
    if section is None:
        return s
    if section == "":
        return f"{_SECRETARIASENADO_ET_BASE}/estatuto_tributario.html#{article}"
    return f"{_SECRETARIASENADO_ET_BASE}/estatuto_tributario_pr{section}.html#{article}"
