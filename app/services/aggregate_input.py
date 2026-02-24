from __future__ import annotations

MAX_INPUT_CHARS = 30000


def aggregate_profile_input(cv_text: str, cover_letters: list[str], max_chars: int = MAX_INPUT_CHARS) -> str:
    normalized_cv = cv_text.strip()
    normalized_letters = [letter.strip() for letter in cover_letters if letter.strip()]

    sections: list[str] = []
    if normalized_cv:
        sections.append("=== CV ===\n" + normalized_cv)

    for idx, letter in enumerate(normalized_letters, start=1):
        sections.append(f"=== COVER_LETTER_{idx} ===\n{letter}")

    full_combined = "\n\n".join(sections).strip()
    if len(full_combined) <= max_chars:
        return full_combined

    prioritized: list[str] = []
    if normalized_cv:
        prioritized.append("=== CV ===\n" + normalized_cv)

    for idx, letter in enumerate(normalized_letters, start=1):
        next_section = f"=== COVER_LETTER_{idx} ===\n{letter}"
        candidate = "\n\n".join(prioritized + [next_section]).strip()
        if len(candidate) <= max_chars:
            prioritized.append(next_section)
            continue

        if prioritized:
            remaining = max_chars - len("\n\n".join(prioritized).strip()) - 2
        else:
            remaining = max_chars
        if remaining > 0:
            prioritized.append(next_section[:remaining])
        break

    reduced = "\n\n".join(prioritized).strip()
    if len(reduced) <= max_chars:
        return reduced
    return reduced[:max_chars]
