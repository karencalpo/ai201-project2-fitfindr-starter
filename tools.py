"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
from importlib import import_module

from utils.data_loader import load_listings

def _load_dotenv_if_available() -> None:
    """Load .env values when python-dotenv is installed."""
    try:
        dotenv = import_module("dotenv")
    except ImportError:
        return

    load_dotenv = getattr(dotenv, "load_dotenv", None)
    if load_dotenv is not None:
        load_dotenv()


_load_dotenv_if_available()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    try:
        groq_module = import_module("groq")
    except ImportError as exc:
        raise ImportError(
            "groq is not installed. Install project dependencies to use LLM tools."
        ) from exc

    Groq = getattr(groq_module, "Groq", None)
    if Groq is None:
        raise ImportError(
            "groq is installed but Groq could not be imported."
        )
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.
    """
    import re
    from collections import Counter

    def normalize(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()

    def tokenize(text: str) -> list[str]:
        return [token for token in normalize(text).split() if token]

    def listing_text(listing: dict) -> str:
        parts = [
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", []) or []),
            " ".join(listing.get("colors", []) or []),
            listing.get("brand") or "",
        ]
        return normalize(" ".join(parts))

    def size_matches(query_size: str | None, listing_size: str | None) -> bool:
        if not query_size:
            return True
        if not listing_size:
            return False

        query_norm = normalize(query_size)
        listing_norm = normalize(listing_size)

        #query_tokens = set(tokenize(query_norm))
        listing_tokens = set(tokenize(listing_norm))

        if query_norm == listing_norm:
            return True

        if query_norm in listing_norm or listing_norm in query_norm:
            return True

        if query_norm in {"s", "small"}:
            return bool({"s", "small"} & listing_tokens) or "s/m" in listing_norm
        if query_norm in {"m", "medium"}:
            return bool({"m", "medium"} & listing_tokens) or any(
                marker in listing_norm for marker in ["s/m", "m/l", "medium", "fits medium"]
            )
        if query_norm in {"l", "large"}:
            return bool({"l", "large"} & listing_tokens) or any(
                marker in listing_norm for marker in ["m/l", "xl", "oversized", "fits oversized"]
            )
        if query_norm in {"xl", "xlarge", "extra large"}:
            return "xl" in listing_norm or "oversized" in listing_norm

        return query_norm in listing_norm or listing_norm in query_norm

    description_tokens = tokenize(description or "")
    if not description_tokens:
        return []

    listings = load_listings()
    scored_results: list[tuple[int, float, str, dict]] = []

    for listing in listings:
        price = listing.get("price")
        if max_price is not None and price is not None and float(price) > float(max_price):
            continue

        if not size_matches(size, listing.get("size")):
            continue

        text = listing_text(listing)
        listing_tokens = tokenize(text)
        token_counts = Counter(listing_tokens)

        overlap_score = 0
        for token in description_tokens:
            if token in token_counts:
                overlap_score += 2

        description_phrase = normalize(description)
        if description_phrase and description_phrase in text:
            overlap_score += 5

        if " ".join(description_tokens) in text:
            overlap_score += 3

        if overlap_score <= 0:
            continue

        title = listing.get("title", "")
        sort_price = float(price) if price is not None else float("inf")
        scored_results.append((overlap_score, sort_price, normalize(title), listing))

    scored_results.sort(key=lambda item: (-item[0], item[1], item[2]))

    return [item[3] for item in scored_results[:3]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.
    ...
    """
    client = _get_groq_client()

    item_description = (
        f"Title: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', '')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Description: {new_item.get('description', '')}"
    )

    wardrobe_items = (wardrobe or {}).get("items") or []

    if not wardrobe_items:
        prompt = (
            f"A user is considering buying this secondhand item:\n\n{item_description}\n\n"
            "They haven't shared their wardrobe yet. Give general styling advice: "
            "what kinds of bottoms, shoes, layers, or accessories pair well with this item, "
            "and what overall vibe or aesthetic it suits. Keep it casual and specific, 2–4 sentences."
        )
    else:
        wardrobe_text = "\n".join(
            f"- {item.get('name', 'Unnamed')} ({item.get('category', '')})"
            f"{': ' + item['notes'] if item.get('notes') else ''}"
            for item in wardrobe_items
        )
        prompt = (
            f"A user is considering buying this secondhand item:\n\n{item_description}\n\n"
            f"Here are the pieces already in their wardrobe:\n{wardrobe_text}\n\n"
            "Suggest 1–2 specific outfit combinations using the new item and named pieces "
            "from the wardrobe. Be specific about which pieces go together and describe the vibe. "
            "Keep it casual and direct, like advice from a stylish friend."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Replace this with your implementation
    return ""
