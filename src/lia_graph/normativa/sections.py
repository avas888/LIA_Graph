from __future__ import annotations

from .policy import (
    NORMATIVA_DEFAULT_SECTION_ID,
    NORMATIVA_DEFAULT_SECTION_TITLE,
    NORMATIVA_SECTION_BLUEPRINTS,
)
from .shared import NormativaSection, clean_text, dedupe_lines, render_bullets, title_hint


def build_lead(anchor_lines: tuple[str, ...]) -> str:
    return anchor_lines[0] if anchor_lines else ""


def build_hierarchy_summary(*, binding_force: str, anchor_title: str) -> str:
    force = clean_text(binding_force, max_chars=120)
    anchor = clean_text(anchor_title, max_chars=140)
    if not force:
        return ""
    if anchor:
        return (
            f"Debe leerse como {force.lower()} y contrastarse con {anchor} "
            "cuando la consulta dependa de desarrollo reglamentario, cambios de vigencia o lectura sistemática."
        )
    return f"Debe leerse como {force.lower()} dentro de la jerarquía normativa aplicable al caso."


def build_applicability_summary(anchor_lines: list[str]) -> str:
    if not anchor_lines:
        return ""
    if len(anchor_lines) == 1:
        return anchor_lines[0]
    return render_bullets(anchor_lines[:3])


def build_professional_impact(*, support_lines: list[str], relation_lines: list[str]) -> str:
    lines: list[str] = []
    if support_lines:
        lines.extend(support_lines[:2])
    if relation_lines:
        lines.append(
            "Conviene validar la vigencia material y la cadena de desarrollo antes de bajar esta lectura a papeles de trabajo o instrucción al cliente."
        )
    return render_bullets(lines)


def build_relations_summary(*, relation_lines: tuple[str, ...], support_lines: tuple[str, ...]) -> str:
    return render_bullets(list(relation_lines or support_lines))


def build_surface_sections(
    *,
    context: dict[str, object],
    applicability_summary: str,
    professional_impact: str,
    relations_summary: str,
) -> tuple[NormativaSection, ...]:
    sections: list[NormativaSection] = []
    field_values = {
        "applicability_summary": applicability_summary,
        "professional_impact": professional_impact,
        "relations_summary": relations_summary,
    }
    for blueprint in NORMATIVA_SECTION_BLUEPRINTS:
        body = str(field_values.get(blueprint.field_name) or "").strip()
        if not body:
            continue
        sections.append(
            NormativaSection(
                id=blueprint.id,
                title=blueprint.title,
                body=body,
            )
        )
    if not sections:
        title = title_hint(context)
        sections.append(
            NormativaSection(
                id=NORMATIVA_DEFAULT_SECTION_ID,
                title=NORMATIVA_DEFAULT_SECTION_TITLE,
                body=(
                    f"{title} requiere contraste con el documento original y con sus desarrollos o modificaciones antes de convertirlo en instrucción cerrada."
                ),
            )
        )
    return tuple(sections)


def build_caution_text(*, missing_primary: bool, has_reforms: bool) -> str:
    if missing_primary:
        return (
            "El grafo no encontró un anclaje primario suficientemente fuerte para enriquecer esta lectura; conviene confirmar el texto vigente en la fuente original."
        )
    if has_reforms:
        return (
            "Revisa si la consulta depende de vigencia material o de una reforma posterior antes de usar esta lectura como criterio definitivo."
        )
    return ""


def build_next_steps(*, title: str, has_support_docs: bool, has_reforms: bool) -> tuple[str, ...]:
    steps: list[str] = [
        f"Abrir el documento original de {title.lower()} y confirmar el texto aplicable al hecho concreto.",
    ]
    if has_reforms:
        steps.append("Contrastar la norma con su cadena de modificación o desarrollo reglamentario más cercana.")
    elif has_support_docs:
        steps.append("Bajar esta lectura a checklist o papeles de trabajo usando el soporte operativo relacionado.")
    return tuple(dedupe_lines(steps, max_items=2))
