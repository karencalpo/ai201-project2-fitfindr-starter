"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "user_request": query,       # original user message
        "description": None,         # parsed item description
        "size": None,                # optional parsed size filter
        "max_price": None,           # optional parsed budget filter
        "wardrobe": wardrobe,        # parsed or provided wardrobe context
        "listings": [],              # full results from search_listings
        "selected_item": None,       # top listing from listings
        "backup_items": [],          # remaining listings after the top result
        "outfit_text": None,         # output from suggest_outfit or fallback
        "fit_card": None,            # output from create_fit_card, or None
        "errors": [],                # list of tool errors encountered
        "status": "searching",       # waiting_for_input | searching | styling | captioning | complete | failed
        "stop_reason": None,         # missing_description | search_failed | no_results
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    import re

    # Step 1: Initialize session
    session = _new_session(query, wardrobe)
    text = query.strip()

    # Step 2: Parse query — extract max_price, size, and description via regex

    # max_price: try range first ("between $100-$200", "$100-$200"), then single cap
    range_pattern = re.compile(
        r'\b(?:between\s+)?\$?\s*\d+(?:\.\d+)?\s*[-–—]\s*\$?\s*(\d+(?:\.\d+)?)'
        r'|\bbetween\s+\$?\s*\d+(?:\.\d+)?\s+and\s+\$?\s*(\d+(?:\.\d+)?)',
        re.IGNORECASE,
    )
    single_price_pattern = re.compile(
        r'\b(?:under|less\s+than|at\s+most|max(?:imum)?|below|up\s+to)\s+\$?\s*(\d+(?:\.\d+)?)'
        r'|\$\s*(\d+(?:\.\d+)?)',
        re.IGNORECASE,
    )
    range_match = range_pattern.search(text)
    if range_match:
        max_price = float(next(g for g in range_match.groups() if g is not None))
        price_span = range_match
    else:
        single_match = single_price_pattern.search(text)
        if single_match:
            max_price = float(single_match.group(1) or single_match.group(2))
            price_span = single_match
        else:
            max_price = None
            price_span = None

    # size: "size M", "size 8", or standalone label (XXS, XS, S, M, L, XL, XXL, XXXL)
    # Negative lookbehind for apostrophe prevents matching the 'm' in "I'm" as size M.
    size_pattern = re.compile(
        r'\bsize\s+([a-zA-Z0-9]+(?:/[a-zA-Z0-9]+)?)\b'
        r"|(?<!')\b(XXS|XS|XXXL|XXL|XL|S|M|L)\b",
        re.IGNORECASE,
    )
    size_match = size_pattern.search(text)
    size = (size_match.group(1) or size_match.group(2)).upper() if size_match else None

    # description: strip price and size fragments from the query text
    desc = text
    if price_span:
        desc = desc[: price_span.start()] + desc[price_span.end() :]
    size_match2 = size_pattern.search(desc)
    if size_match2:
        desc = desc[: size_match2.start()] + desc[size_match2.end() :]

    # strip budget/price sentences that weren't caught above
    desc = re.sub(r'\b(?:my\s+)?budget\s+is\b[^.!?]*[.!?]?', '', desc, flags=re.IGNORECASE)

    # remove leading intent phrases ("I'm looking for", "looking for", "I want", etc.)
    desc = re.sub(
        r"^\s*(?:i'?m\s+|i\s+am\s+)?(?:looking\s+for|searching\s+for|i\s+want|i\s+need|find\s+me|show\s+me|get\s+me)\b",
        '',
        desc,
        flags=re.IGNORECASE,
    )
    desc = re.sub(r'\b(?:in|for|at|a|an|the)\s*$', '', desc, flags=re.IGNORECASE)
    desc = re.sub(r'\s+', ' ', desc).strip().strip(',').strip('.'). strip()

    # Step 2 (continued): If description is missing or blank, stop and ask for clarification
    if not desc:
        session["status"] = "waiting_for_input"
        session["stop_reason"] = "missing_description"
        session["errors"].append("What item are you looking for?")
        return session

    session["description"] = desc
    session["size"] = size
    session["max_price"] = max_price

    # Step 3: Call search_listings; stop on tool failure
    try:
        results = search_listings(desc, size, max_price)
        session["listings"] = results
    except Exception as exc:
        session["status"] = "failed"
        session["stop_reason"] = "search_failed"
        session["errors"].append(str(exc))
        return session

    # Step 5: If no results, stop with retry guidance
    if not results:
        session["status"] = "failed"
        session["stop_reason"] = "no_results"
        parts = [f'No listings found for "{desc}".']
        if size:
            parts.append(f'Size filter "{size}" may be too restrictive — try removing it.')
        if max_price is not None:
            parts.append(f'Budget of ${max_price:.0f} may be too low — try raising it.')
        parts.append("You can also try a broader description (e.g., \"flowy dress\" instead of \"designer ballgown\").")
        session["errors"].append(" ".join(parts))
        return session

    # Step 6: Select top result; keep the rest as backups
    session["selected_item"] = results[0]
    session["backup_items"] = results[1:]

    # Step 7: Call suggest_outfit; fall back to a generic tip on failure
    session["status"] = "styling"
    try:
        outfit_text = suggest_outfit(new_item=results[0], wardrobe=wardrobe)
        if not outfit_text or not outfit_text.strip():
            raise ValueError("empty response")
    except Exception as exc:
        session["errors"].append(str(exc))
        title = results[0].get("title", "this item")
        outfit_text = (
            f"This {title} is a versatile piece. "
            "Try pairing it with neutral bottoms and clean sneakers for an effortless everyday look."
        )
    session["outfit_text"] = outfit_text

    # Steps 10–12: Call create_fit_card; set fit_card to None on failure, then continue
    session["status"] = "captioning"
    try:
        fit_card = create_fit_card(outfit=outfit_text, new_item=results[0])
        if not fit_card or not fit_card.strip():
            raise ValueError("empty response")
        session["fit_card"] = fit_card
    except Exception as exc:
        session["errors"].append(str(exc))
        session["fit_card"] = None

    # Step 14: Mark complete and return
    session["status"] = "complete"
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: midi dress ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["stop_reason"]:
        print(f"Stop reason: {session['stop_reason']}")
        print(f"Errors: {session['errors']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_text']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Stop reason: {session2['stop_reason']}")
    print(f"Errors: {session2['errors']}")
    print(f"\nFit card: {session2['fit_card']}")
