"""Byte-exact prompt rendering from bundle instruction segments.

Each function reproduces the legacy in-route string assembly exactly:
Python ``%``-formatting against the same argument tuples, in the same
order, with no added or removed bytes. A zero-byte constitution renders
only the instruction — no separator, newline, or whitespace (frozen
contract §1) — so rendering starts from the segment bytes alone.
"""


def _template(bundle, name):
    constitution = bundle.segments.get("constitution", "")
    # Slice 1 constitutions are zero-byte by contract; the loader enforces
    # it. Concatenation without any separator is the frozen rendering rule.
    return constitution + bundle.segments[name]


def render_coach_system(bundle, level, family, competency, grounding,
                        allowed_dimension_keys):
    return _template(bundle, "system_template") % (
        level, family, competency, grounding, allowed_dimension_keys,
    )


def render_coach_user(bundle, question, opportunity_block, answer):
    return _template(bundle, "user_template") % (
        question, opportunity_block, answer,
    )


def render_revision_system(bundle, evidence_lines):
    return _template(bundle, "system_template") % (evidence_lines,)


def render_revision_user(bundle, question, family, opportunity_block, answer,
                         confirmed_context, improvement_notes):
    return _template(bundle, "user_template") % (
        question, family, opportunity_block, answer, confirmed_context,
        improvement_notes,
    )


def render_planning_hints_system(bundle):
    return _template(bundle, "system_template")


def render_planning_hints_user(bundle, question, level, family, competency,
                               practice_mode, opportunity_block):
    return _template(bundle, "user_template") % (
        question, level, family, competency, practice_mode, opportunity_block,
    )


def render_grounded_system(bundle, level, family, evidence_lines):
    return _template(bundle, "system_template") % (
        level, family, evidence_lines,
    )


def render_generic_system(bundle, level, family):
    return _template(bundle, "system_template") % (level, family)


def render_model_answer_user(bundle, question, opportunity_block):
    """The shared base user content for grounded and generic answers."""
    return _template(bundle, "user_template") % (question, opportunity_block)


def render_grounded_followup_suffix(bundle, prior_answer, follow_up):
    return bundle.segments["followup_suffix_template"] % (
        prior_answer, follow_up,
    )


def render_generic_followup_suffix(bundle, follow_up):
    return bundle.segments["followup_suffix_template"] % (follow_up,)


def render_generic_followup_prior_best_practice(bundle, prior_answer):
    return bundle.segments["followup_prior_best_practice_template"] % (
        prior_answer,
    )


def render_generic_followup_prior_compare(bundle, prior_illustrative_answer):
    return bundle.segments["followup_prior_compare_template"] % (
        prior_illustrative_answer,
    )
