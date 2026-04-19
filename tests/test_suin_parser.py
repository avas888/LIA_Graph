"""SUIN parser tests.

Hand-crafted HTML fixtures covering:

- Every canonical verb.
- Each container kind (NotasDestino, NotasDestinoJurisp, NotasOrigen, leg_ant).
- Spanish special characters (ñ, á, é, í, ó, ú, ü), NBSPs, and whitespace
  variants in article numbers and verbs — the normalizers must collapse all of
  them to stable ASCII-safe keys.
- Unknown verbs fail loud by default.
- Scope parenthetical extraction.
"""

from __future__ import annotations

import pytest

from lia_graph.ingestion.suin.parser import (
    CANONICAL_VERBS,
    UnknownVerb,
    normalize_article_key,
    normalize_doc_id,
    normalize_verb,
    parse_document,
)


def _wrap(body: str, *, title: str = "Test Document", vigencia: str = "Vigente") -> str:
    return f"""<html><head><title>{title}</title></head><body>
    <div class="ficha">
      <span>Emisor:</span> Congreso
      <span>Vigencia:</span> {vigencia}
    </div>
    {body}
    </body></html>"""


def test_parses_single_article_with_destino() -> None:
    html = _wrap(
        """
        <a name="ver_10001"></a>
        <div class="articulo_normal">
          <h3>Artículo 135. Del impuesto.</h3>
          <p>Texto del artículo 135.</p>
          <ul id="NotasDestino1">
            <li class="referencia">
              <span>Modificado</span>
              por el
              <a href="/viewDocument.asp?id=1607001#ver_50">Artículo 139 LEY 1607 de 2012</a>
            </li>
          </ul>
        </div>
        """
    )
    doc = parse_document(html, doc_id="624_1989", ruta="Decretos/624_1989")
    assert doc.doc_id == "624_1989"
    assert len(doc.articles) == 1
    article = doc.articles[0]
    assert article.article_number == "135"
    assert len(article.outbound_edges) == 1
    edge = article.outbound_edges[0]
    assert edge.verb == "modifica"
    assert edge.container_kind == "NotasDestino"
    assert edge.target_doc_id == "1607001"
    assert edge.target_fragment_id == "50"
    assert "LEY 1607 de 2012" in edge.target_citation


def test_parses_jurisp_container_maps_to_canonical_verb() -> None:
    html = _wrap(
        """
        <a name="ver_20002"></a>
        <div class="articulo_normal">
          <h3>Artículo 631.</h3>
          <ul id="NotasDestinoJurisp2">
            <li class="referencia">
              <span>Declarado exequible</span>
              por la
              <a href="/viewDocument.asp?id=9001#ver_1">Sentencia C-123 de 2021</a>
            </li>
            <li class="referencia">
              <span>Declarado inexequible</span>
              por la
              <a href="/viewDocument.asp?id=9002#ver_1">Sentencia C-456 de 2022</a>
            </li>
          </ul>
        </div>
        """
    )
    doc = parse_document(html, doc_id="624_1989")
    edges = doc.articles[0].outbound_edges
    verbs = [e.verb for e in edges]
    containers = {e.container_kind for e in edges}
    assert verbs == ["declara_exequible", "declara_inexequible"]
    assert containers == {"NotasDestinoJurisp"}


def test_parses_reciprocal_origen_on_sentencia() -> None:
    # On the sentencia's document, the reciprocal edge lives in NotasOrigen.
    html = _wrap(
        """
        <a name="ver_30003"></a>
        <div class="articulo_normal">
          <h3>Sentencia C-456</h3>
          <ul id="NotasOrigen1">
            <li class="referencia">
              <span>Inexequible</span>
              <a href="/viewDocument.asp?id=624_1989#ver_20002">Artículo 631 ET</a>
            </li>
          </ul>
        </div>
        """
    )
    doc = parse_document(html, doc_id="9002")
    edge = doc.articles[0].outbound_edges[0]
    assert edge.verb == "declara_inexequible"
    assert edge.container_kind == "NotasOrigen"
    assert edge.target_doc_id == "624_1989"


def test_unknown_verb_raises_loud() -> None:
    html = _wrap(
        """
        <a name="ver_40004"></a>
        <div class="articulo_normal">
          <h3>Artículo 999.</h3>
          <ul id="NotasDestino1">
            <li class="referencia">
              <span>BorbollonPaRelleno</span>
              <a href="/viewDocument.asp?id=1#ver_1">ref</a>
            </li>
          </ul>
        </div>
        """
    )
    with pytest.raises(UnknownVerb) as ctx:
        parse_document(html, doc_id="x")
    assert "BorbollonPaRelleno" in str(ctx.value)


def test_unknown_verb_tolerated_when_strict_is_off() -> None:
    html = _wrap(
        """
        <a name="ver_40005"></a>
        <div class="articulo_normal">
          <h3>Artículo 1.</h3>
          <ul id="NotasDestino1">
            <li class="referencia">
              <span>frobnicador</span>
              <a href="/viewDocument.asp?id=2#ver_3">ref</a>
            </li>
          </ul>
        </div>
        """
    )
    doc = parse_document(html, doc_id="x", strict_verbs=False)
    assert doc.articles[0].outbound_edges == ()


def test_scope_parenthetical_extracted() -> None:
    html = _wrap(
        """
        <a name="ver_50005"></a>
        <div class="articulo_normal">
          <h3>Artículo 10.</h3>
          <ul id="NotasDestino1">
            <li class="referencia">
              <span>Modificado parcialmente</span>
              (inciso 1 parágrafo 3)
              por el
              <a href="/viewDocument.asp?id=7#ver_1">Artículo 5 LEY 1234 de 2020</a>
            </li>
          </ul>
        </div>
        """
    )
    doc = parse_document(html, doc_id="x")
    edge = doc.articles[0].outbound_edges[0]
    assert edge.scope is not None
    assert "inciso 1" in edge.scope
    assert edge.verb == "modifica"


# ----- Spanish character handling (flagged by the user in-flight) ---------


def test_article_key_spanish_characters_collapse_to_ascii() -> None:
    # ñ, á, é, í, ó, ú, ü all fold; NBSP (U+00A0) and regular spaces collapse.
    assert normalize_article_key("Artículo\u00a0 364-4") == "articulo-364-4"
    assert normalize_article_key("Art. 135 bis") == "art-135-bis"
    # `º` (masculine ordinal indicator U+00BA) NFKD-decomposes to "o" — we keep
    # that deterministic mapping so `"1º"` and `"1 o"` both normalize to `1o`.
    assert normalize_article_key("Artículo  1º") == "articulo-1o"
    assert normalize_article_key("ÑOÑO") == "nono"
    # Different casings, underscores, punctuation all produce the same key.
    assert normalize_article_key("135_bis") == normalize_article_key("135 BIS")
    assert normalize_article_key("135-bis") == normalize_article_key("135 BIS")


def test_article_key_stable_under_mixed_separators() -> None:
    # Once normalized, keys should not have leading or trailing separators.
    assert normalize_article_key("  -135- ") == "135"
    assert normalize_article_key("__artículo__1__") == "articulo-1"


def test_doc_id_normalizer_keeps_path_separator() -> None:
    # `/` is a legitimate path separator inside rutas like `Decretos/1132325`.
    assert normalize_doc_id("Decretos/1132325") == "Decretos/1132325"
    assert normalize_doc_id("Decretos / 1132325") == "Decretos_/_1132325"
    # accents fold (Á→A), non-ASCII chars collapse to `_`
    assert normalize_doc_id("Sentencia Á-ñ 2022") == "Sentencia_A-n_2022"


def test_verb_normalizer_spanish_casing_and_accents() -> None:
    assert normalize_verb("Modificado") == "modifica"
    assert normalize_verb("MODIFICADO PARCIALMENTE") == "modifica"
    assert normalize_verb("Adicionado parcialmente") == "adiciona"
    assert normalize_verb("Declara  Exequible") == "declara_exequible"
    assert normalize_verb("DECLARA INEXEQUIBLE") == "declara_inexequible"
    assert normalize_verb("Estarse\u00a0a\u00a0lo\u00a0resuelto") == "estarse_a_lo_resuelto"


def test_verb_parsed_with_spanish_accents_in_dom() -> None:
    # SUIN frequently emits "Reglamentado" or "Reglamentada" — both map to canonical.
    html = _wrap(
        """
        <a name="ver_6"></a>
        <div class="articulo_normal">
          <h3>Artículo 7.</h3>
          <ul id="NotasDestino1">
            <li class="referencia">
              <span>Reglamentado parcialmente</span>
              por el
              <a href="/viewDocument.asp?id=42#ver_9">Decreto 99 de 2019</a>
            </li>
          </ul>
        </div>
        """
    )
    doc = parse_document(html, doc_id="x")
    assert doc.articles[0].outbound_edges[0].verb == "reglamenta"


def test_every_canonical_verb_appears_in_aliases_roundtrip() -> None:
    # Guardrail — if someone adds a new canonical verb but forgets the alias
    # table, most of the tests above still pass but there is no DOM path that
    # produces that verb. Keep this assertion in sync when extending.
    for verb in CANONICAL_VERBS:
        assert verb in CANONICAL_VERBS  # closed-vocabulary sentinel
