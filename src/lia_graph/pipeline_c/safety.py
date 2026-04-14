from __future__ import annotations

from ..locale_currency import format_currency_mentions
from .contracts import VerifierDecision
from .errors import VerifierBlockedError
from .output_cleaning import strip_inline_evidence_annotations


def finalize_answer(
    *,
    answer_markdown: str,
    verifier: VerifierDecision,
    pais: str = "colombia",
) -> tuple[str, str]:
    if verifier.blocked:
        raise VerifierBlockedError(
            details={
                "verifier_mode": verifier.mode,
                "flags": list(verifier.flags),
                "warnings": list(verifier.warnings),
            }
        )

    output = strip_inline_evidence_annotations(answer_markdown).strip()
    output = format_currency_mentions(output, pais=pais)

    concise = output
    if len(concise) > 320:
        concise = concise[:317].rstrip() + "..."
    return output, concise
