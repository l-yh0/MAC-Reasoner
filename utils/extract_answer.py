"""Helpers for extracting boxed answers from model responses."""

import re


def extract_answer(text: str):
    """
    Extract the last \\boxed{...} value and unwrap common LaTeX wrappers.
    """
    if not text:
        return None

    # Match the last \boxed{...}, allowing multiline content.
    matches = re.findall(r"\\boxed\s*{([^{}]*(?:{[^{}]*}[^{}]*)*)}", text, re.DOTALL)
    if not matches:
        return None
    content = matches[-1].strip()

    # Strip common wrapper commands such as \text{...} and \mathrm{...}.
    while True:
        m = re.match(r"\\(?:text|mathrm|mbox|textrm)\s*{(.+)}$", content, re.DOTALL)
        if not m:
            break
        content = m.group(1).strip()

    # Remove leading/trailing punctuation while preserving brackets.
    return content.strip(" \t\n\r.,;:!?，。、；：？！“”‘’'\"·") or None


def clean_response(text):
    """Remove intermediate <think> blocks from a model response."""
    clean_resp = re.sub(r"<think>.*?</think>\n", "", text, flags=re.DOTALL)
    return clean_resp
