"""Mistake taxonomy: maps the LLM's granular `subtype` to one of the four linguistic pillars.

The LLM is good at granular labels (articles, prepositions, …) but should not pick our 4-pillar
abstraction. It emits a `MistakeSubtype`; the backend deterministically derives the
`LinguisticCategory` (pillar) here. This module is the single source of truth for that mapping.
"""

from __future__ import annotations

from .models import LinguisticCategory, MistakeSubtype

# Every subtype maps to exactly one pillar. Keep this exhaustive so `pillar_for` is total.
SUBTYPE_TO_PILLAR: dict[MistakeSubtype, LinguisticCategory] = {
    # syntax — structure: articles, prepositions, tense, word order
    MistakeSubtype.articles: LinguisticCategory.syntax,
    MistakeSubtype.prepositions: LinguisticCategory.syntax,
    MistakeSubtype.verb_tenses: LinguisticCategory.syntax,
    MistakeSubtype.word_order: LinguisticCategory.syntax,
    # semantics — meaning: word choice, clarity
    MistakeSubtype.vocabulary: LinguisticCategory.semantics,
    MistakeSubtype.clarity: LinguisticCategory.semantics,
    # orthography — written form: spelling, (pronunciation dormant until Voice/PR16)
    MistakeSubtype.spelling: LinguisticCategory.orthography,
    MistakeSubtype.pronunciation: LinguisticCategory.orthography,
    # living_communication — natural use: idioms, phrasal verbs, naturalness
    MistakeSubtype.idioms: LinguisticCategory.living_communication,
    MistakeSubtype.naturalness: LinguisticCategory.living_communication,
    # fallback
    MistakeSubtype.other: LinguisticCategory.semantics,
}


def pillar_for(subtype: MistakeSubtype) -> LinguisticCategory:
    """Deterministically resolve a subtype to its linguistic pillar."""
    return SUBTYPE_TO_PILLAR.get(subtype, LinguisticCategory.semantics)
