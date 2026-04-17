from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]{1,220})\]\((https?://[^)\s]+)\)", re.IGNORECASE)
_RAW_URL_RE = re.compile(r"https?://[^\s<>'\"`]+", re.IGNORECASE)
_HEADING_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
_BOLD_BULLET_LABEL_RE = re.compile(r"^\s*[-*+]?\s*\*\*(.+?)\*\*\s*(?:[—–-]|:)")
_PROVIDER_TITLE_SPLIT_RE = re.compile(r"\s+[—–-]\s+")
_NUMBERING_PREFIX_RE = re.compile(r"^(?:[A-Z]\d+\s+[—-]\s+)?(?:\d+(?:\.\d+){0,4}\.?\s+)+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_WORD_BOUNDARY_CACHE: dict[str, re.Pattern[str]] = {}


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    aliases: tuple[str, ...]
    domains: tuple[str, ...] = ()


_PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(name="Actualícese", aliases=("Actualícese", "Actualicese"), domains=("actualicese.com",)),
    ProviderSpec(
        name="Alegra",
        aliases=("Alegra", "Siempre al Día", "Siempre al Dia", "Siempre al Día (Alegra)", "Siempre al Dia (Alegra)"),
        domains=("alegra.com", "siemprealdia.co"),
    ),
    ProviderSpec(name="Accounter", aliases=("Accounter",), domains=("accounter.co",)),
    ProviderSpec(
        name="Ámbito Jurídico",
        aliases=("Ámbito Jurídico", "Ambito Jurídico", "Ámbito Juridico", "Ambito Juridico"),
        domains=("ambitojuridico.com",),
    ),
    ProviderSpec(
        name="Amézquita",
        aliases=("Amézquita", "Amezquita", "Amézquita & Cía", "Amézquita & Cia", "Amezquita & Cía", "Amezquita & Cia"),
        domains=("amezquita.com.co",),
    ),
    ProviderSpec(name="Baker Tilly", aliases=("Baker Tilly",), domains=("bakertilly.com", "bakertilly.com.co")),
    ProviderSpec(name="BDO", aliases=("BDO", "BDO Colombia"), domains=("bdo.com", "bdo.com.co")),
    ProviderSpec(name="Bloomberg Línea", aliases=("Bloomberg Línea", "Bloomberg Linea"), domains=("bloomberglinea.com",)),
    ProviderSpec(name="Brigard Urrutia", aliases=("Brigard Urrutia",), domains=("bu.com.co",)),
    ProviderSpec(name="Chapman Wilches", aliases=("Chapman Wilches",), domains=("chapmanwilches.com",)),
    ProviderSpec(name="CIJUF", aliases=("CIJUF",), domains=("cijuf.org.co",)),
    ProviderSpec(name="CMS Law", aliases=("CMS Law", "CMS", "CMS Colombia"), domains=("cms.law",)),
    ProviderSpec(name="ConsultorContable", aliases=("ConsultorContable", "Consultor Contable"), domains=("consultorcontable.com",)),
    ProviderSpec(name="CR Consultores", aliases=("CR Consultores",), domains=("crconsultorescolombia.com",)),
    ProviderSpec(name="Crowe Colombia", aliases=("Crowe Colombia", "Crowe"), domains=("crowe.com",)),
    ProviderSpec(name="Deloitte", aliases=("Deloitte", "Deloitte Colombia"), domains=("deloitte.com", "www2.deloitte.com")),
    ProviderSpec(name="El Tiempo", aliases=("El Tiempo",), domains=("eltiempo.com",)),
    ProviderSpec(name="EY", aliases=("EY", "EY Colombia", "EY Tax News"), domains=("ey.com",)),
    ProviderSpec(name="Gerencie.com", aliases=("Gerencie.com", "Gerencie"), domains=("gerencie.com",)),
    ProviderSpec(name="GlobalContable", aliases=("GlobalContable",), domains=("globalcontable.com",)),
    ProviderSpec(
        name="Gómez-Pinzón",
        aliases=("Gómez-Pinzón", "Gomez-Pinzon", "Gómez Pinzón", "Gomez Pinzon"),
        domains=("gomezpinzon.com",),
    ),
    ProviderSpec(name="Grant Thornton", aliases=("Grant Thornton",), domains=("grantthornton.com", "grantthornton.com.co")),
    ProviderSpec(name="Herrera & Asociados", aliases=("Herrera & Asociados", "Herrera y Asociados"), domains=("herreraasociados.co",)),
    ProviderSpec(name="Holland & Knight", aliases=("Holland & Knight", "Holland and Knight", "H&K"), domains=("hklaw.com",)),
    ProviderSpec(name="INCP", aliases=("INCP",), domains=("incp.org.co",)),
    ProviderSpec(name="Infobae", aliases=("Infobae", "Infobae Colombia"), domains=("infobae.com",)),
    ProviderSpec(name="KPMG", aliases=("KPMG", "KPMG TaxNewsFlash", "KPMG Tax News Flash"), domains=("kpmg.com",)),
    ProviderSpec(name="LAV Tributaria", aliases=("LAV Tributaria",), domains=("lavtributaria.com",)),
    ProviderSpec(name="Legis", aliases=("Legis", "Legis Colombia", "Legis Streaming"), domains=("legis.com.co",)),
    ProviderSpec(name="Nieto Lawyers", aliases=("Nieto Lawyers",), domains=("nietolawyers.com",)),
    ProviderSpec(
        name="Peña Molina & Asociados",
        aliases=("Peña Molina & Asociados", "Pena Molina & Asociados", "PMA"),
        domains=("pma.com.co",),
    ),
    ProviderSpec(
        name="Pérez-Llorca",
        aliases=("Pérez-Llorca", "Perez-Llorca", "Pérez Llorca", "Perez Llorca"),
        domains=("perezllorca.com",),
    ),
    ProviderSpec(name="PGP Abogados", aliases=("PGP Abogados", "PGP Legal"), domains=("pgplegal.com",)),
    ProviderSpec(
        name="PHR (Posse Herrera Ruiz)",
        aliases=("PHR (Posse Herrera Ruiz)", "PHR Legal", "PHR", "Posse Herrera Ruiz"),
        domains=("phrlegal.com",),
    ),
    ProviderSpec(name="PwC", aliases=("PwC", "PWC", "PricewaterhouseCoopers"), domains=("pwc.com",)),
    ProviderSpec(name="Río Consultores", aliases=("Río Consultores", "Rio Consultores"), domains=("rioconsultores.com",)),
    ProviderSpec(name="Tower Consulting", aliases=("Tower Consulting",), domains=("tower-consulting.com",)),
)

_NON_PROVIDER_LABELS = {
    "authority",
    "archivo",
    "audiencia",
    "base gravable",
    "beneficio de auditoria",
    "beneficio de auditoría",
    "calculodelincremento",
    "calculo del incremento",
    "certificado de intereses",
    "compilado",
    "condiciones de aplicacion",
    "condiciones de aplicación",
    "contexto",
    "corpus",
    "estado normativo",
    "fuente",
    "fuente primaria",
    "fuente primaria de referencia",
    "fuentes interpretativas por tema referencia rapida",
    "fuentes interpretativas por tema referencia rápida",
    "identificacion",
    "identificación",
    "interpretaciones por fuente",
    "presencia economica significativa",
    "presencia económica significativa",
    "regla operativa",
    "regla operativa para lia",
    "relaciones normativas",
    "retenciones",
    "riesgos de interpretacion",
    "riesgos de interpretación",
    "tasa minima de tributacion depurada",
    "tasa mínima de tributación depurada",
    "texto base referenciado",
    "usuario",
}
_NON_PROVIDER_AUTHORITY_LABELS = {"dian", "fuente profesional", "minhacienda", "suin", "usuario"}


def _normalize_provider_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " y ")
    text = text.replace("/", " / ")
    text = _NON_ALNUM_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_boundary_pattern(alias: str) -> re.Pattern[str]:
    cached = _WORD_BOUNDARY_CACHE.get(alias)
    if cached is not None:
        return cached
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")
    _WORD_BOUNDARY_CACHE[alias] = pattern
    return pattern


def _alias_entries() -> tuple[tuple[re.Pattern[str], str, int], ...]:
    entries: list[tuple[re.Pattern[str], str, int]] = []
    for spec in _PROVIDER_SPECS:
        labels = {spec.name, *spec.aliases}
        for alias in labels:
            normalized = _normalize_provider_text(alias)
            if not normalized:
                continue
            entries.append((_word_boundary_pattern(normalized), spec.name, len(normalized)))
    entries.sort(key=lambda item: item[2], reverse=True)
    return tuple(entries)


def _domain_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in _PROVIDER_SPECS:
        for domain in spec.domains:
            clean = str(domain or "").strip().lower()
            if clean:
                mapping[clean] = spec.name
    return mapping


_ALIAS_ENTRIES = _alias_entries()
_DOMAIN_MAP = _domain_map()


def canonical_provider_name(value: Any) -> str | None:
    normalized = _normalize_provider_text(value)
    if not normalized or normalized in _NON_PROVIDER_AUTHORITY_LABELS:
        return None
    for pattern, canonical_name, _ in _ALIAS_ENTRIES:
        match = pattern.search(normalized)
        if match and match.start() == 0 and match.end() == len(normalized):
            return canonical_name
    return None


def provider_from_domain(url: str) -> str | None:
    try:
        domain = urlparse(str(url or "").strip()).netloc.lower().replace("www.", "")
    except ValueError:
        return None
    if not domain:
        return None
    for candidate, provider in _DOMAIN_MAP.items():
        if domain == candidate or domain.endswith(f".{candidate}"):
            return provider
    return None


def provider_names_from_label(label: Any) -> list[str]:
    normalized = _normalize_provider_text(label)
    if not normalized or normalized in _NON_PROVIDER_LABELS:
        return []
    candidates: list[tuple[int, int, str]] = []
    for pattern, canonical_name, alias_len in _ALIAS_ENTRIES:
        match = pattern.search(normalized)
        if match:
            candidates.append((match.start(), -alias_len, canonical_name))
    if not candidates:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for _, _, canonical_name in sorted(candidates):
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        ordered.append(canonical_name)
    return ordered


def normalize_provider_payload(value: Any) -> list[dict[str, str | None]]:
    normalized: list[dict[str, str | None]] = []
    seen: set[str] = set()
    if isinstance(value, str):
        items: list[Any] = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = []
    for item in items:
        if isinstance(item, dict):
            label = str(item.get("name") or item.get("provider") or "").strip()
            url = str(item.get("url") or "").strip() or None
            names = provider_names_from_label(label) or ([canonical_provider_name(label)] if canonical_provider_name(label) else [])
        else:
            url = None
            names = provider_names_from_label(item) or ([canonical_provider_name(item)] if canonical_provider_name(item) else [])
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            normalized.append({"name": name, "url": url})
    return normalized


def extract_expert_providers(
    text: str,
    *,
    stored_providers: Any = None,
    stored_labels: Any = None,
    authority: Any = None,
    max_providers: int = 12,
) -> list[dict[str, str | None]]:
    providers: list[dict[str, str | None]] = []
    seen: dict[str, int] = {}

    def _append(name: str | None, *, url: str | None = None) -> None:
        clean_name = str(name or "").strip()
        if not clean_name:
            return
        clean_url = str(url or "").strip() or None
        index = seen.get(clean_name)
        if index is None:
            seen[clean_name] = len(providers)
            providers.append({"name": clean_name, "url": clean_url})
            return
        if providers[index]["url"] is None and clean_url:
            providers[index]["url"] = clean_url

    for item in normalize_provider_payload(stored_providers):
        _append(str(item.get("name") or "").strip(), url=str(item.get("url") or "").strip() or None)
        if len(providers) >= max_providers:
            return providers[:max_providers]

    for item in normalize_provider_payload(stored_labels):
        _append(str(item.get("name") or "").strip(), url=str(item.get("url") or "").strip() or None)
        if len(providers) >= max_providers:
            return providers[:max_providers]

    raw_text = str(text or "")
    if raw_text:
        for line in raw_text.splitlines():
            for label, url in _MARKDOWN_LINK_RE.findall(line):
                names = provider_names_from_label(label)
                if not names:
                    domain_provider = provider_from_domain(url)
                    names = [domain_provider] if domain_provider else []
                for provider_name in names:
                    _append(provider_name, url=url)
                    if len(providers) >= max_providers:
                        return providers[:max_providers]

            heading_match = _HEADING_LINE_RE.match(line)
            if heading_match:
                heading_text = _PROVIDER_TITLE_SPLIT_RE.split(heading_match.group(1), maxsplit=1)[0]
                heading_text = _NUMBERING_PREFIX_RE.sub("", heading_text).strip(" :-\u2013\u2014")
                for provider_name in provider_names_from_label(heading_text):
                    _append(provider_name)
                    if len(providers) >= max_providers:
                        return providers[:max_providers]

            bullet_match = _BOLD_BULLET_LABEL_RE.match(line)
            if bullet_match:
                label = _NUMBERING_PREFIX_RE.sub("", bullet_match.group(1)).strip(" :-\u2013\u2014")
                raw_urls = list(_RAW_URL_RE.findall(line))
                fallback_url = raw_urls[0] if raw_urls else None
                for provider_name in provider_names_from_label(label):
                    _append(provider_name, url=fallback_url)
                    if len(providers) >= max_providers:
                        return providers[:max_providers]

            for raw_url in _RAW_URL_RE.findall(line):
                provider_name = provider_from_domain(raw_url)
                if provider_name:
                    _append(provider_name, url=raw_url)
                    if len(providers) >= max_providers:
                        return providers[:max_providers]

    authority_provider = canonical_provider_name(authority)
    if authority_provider:
        _append(authority_provider)
    return providers[:max_providers]


def provider_labels(providers: Any) -> list[str]:
    if not isinstance(providers, (list, tuple, set)):
        return []
    labels: list[str] = []
    seen: set[str] = set()
    for item in providers:
        if isinstance(item, dict):
            label = str(item.get("name") or item.get("provider") or "").strip()
        else:
            label = str(item or "").strip()
        canonical = canonical_provider_name(label) or label
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        labels.append(canonical)
    return labels


__all__ = [
    "canonical_provider_name",
    "extract_expert_providers",
    "normalize_provider_payload",
    "provider_from_domain",
    "provider_labels",
    "provider_names_from_label",
]
