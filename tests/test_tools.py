import os
from importlib.util import find_spec
import pytest
import tools
from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe, load_listings

def _get_listing_by_id(listing_id: str) -> dict:
    listing = next((item for item in load_listings() if item.get("id") == listing_id), None)
    if listing is None:
        raise AssertionError(f"Fixture listing {listing_id!r} was not found in data/listings.json")
    return listing


SAMPLE_ITEM = _get_listing_by_id("lst_006")
SAMPLE_WARDROBE = get_example_wardrobe()


class _FakeGroqResponse:
    def __init__(self, content: str):
        self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]


class _FakeCompletions:
    def create(self, model: str, messages: list[dict], temperature: float):
        import re

        prompt = messages[0]["content"].lower()

        if "haven't shared their wardrobe yet" in prompt:
            return _FakeGroqResponse(
                "Wardrobe is empty, so here is a general styling plan: pair this with straight-leg denim, "
                "clean sneakers, and a light jacket for balance."
            )

        if "here are the pieces already in their wardrobe" in prompt:
            return _FakeGroqResponse(
                "Style this with your black jeans and white sneakers, then add the denim jacket for a relaxed look."
            )

        item_match = re.search(r"the thrifted item: (.*?) off ", prompt)
        platform_match = re.search(r" off (.*?) for ", prompt)
        price_match = re.search(r" for (\$[^.\n]+)", prompt)

        item_name = item_match.group(1) if item_match else "thrifted find"
        platform = platform_match.group(1) if platform_match else "marketplace"
        price = price_match.group(1) if price_match else "$0"

        return _FakeGroqResponse(
            f"thrift score: built a relaxed look around the {item_name}, then finished it with clean sneakers and a light jacket. "
            f"found it on {platform} for {price}, and it ties the whole outfit together."
        )


class _FakeGroqClient:
    def __init__(self):
        self.chat = type("Chat", (), {"completions": _FakeCompletions()})()


@pytest.fixture
def fake_groq(monkeypatch):
    monkeypatch.setattr(tools, "_get_groq_client", lambda: _FakeGroqClient())


def _require_groq_key():
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY is not set; skipping live Groq integration tests.")
    if find_spec("groq") is None:
        pytest.skip("groq package is not installed; skipping live Groq integration tests.")


def test_search_listings_vintage_graphic_tee_with_size_and_budget_returns_3():
    results = search_listings("vintage graphic tee", size="M", max_price=30)

    assert isinstance(results, list)
    assert len(results) == 3
    assert all(isinstance(item, dict) for item in results)
    assert all(item["price"] <= 30 for item in results)
    assert any(
        "graphic tee" in (item.get("title", "") + " " + " ".join(item.get("style_tags", []))).lower()
        or "graphic" in item.get("description", "").lower()
        for item in results
    )


def test_search_listings_oversized_blazer_without_filters_returns_results():
    results = search_listings("oversized blazer")

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(item, dict) for item in results)
    assert all("title" in item and "price" in item for item in results)


def test_search_listings_no_matches_returns_empty_list_per_planning_spec():
    results = search_listings("diamond-encrusted space tuxedo", size="XXS", max_price=1)

    assert isinstance(results, list)
    assert results == []


def test_suggest_outfit_with_wardrobe_returns_nonempty_styling_text(fake_groq):
    result = suggest_outfit(SAMPLE_ITEM, SAMPLE_WARDROBE)

    assert isinstance(result, str)
    assert result.strip() != ""
    assert len(result.strip()) >= 20


def test_suggest_outfit_with_empty_wardrobe_returns_specific_message(fake_groq):
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    lower = result.lower()

    assert isinstance(result, str)
    assert result.strip() != ""
    assert "wardrobe is empty" in lower
    assert any(word in lower for word in ["pair", "sneakers", "jacket", "styling"])


def test_suggest_outfit_handles_missing_items_key_gracefully(fake_groq):
    result = suggest_outfit(SAMPLE_ITEM, {})

    assert isinstance(result, str)
    assert "wardrobe is empty" in result.lower()


def test_create_fit_card_with_complete_input_returns_caption_with_price_and_platform(fake_groq):

    outfit = (
        "Pair the faded band tee with baggy dark-wash jeans and chunky white sneakers. "
        "Add a light bomber jacket for a relaxed 90s streetwear vibe."
    )
    caption = create_fit_card(outfit, SAMPLE_ITEM)

    assert isinstance(caption, str)
    assert caption.strip() != ""
    price_value = SAMPLE_ITEM["price"]
    expected_price_variants = {str(price_value)}
    if isinstance(price_value, (int, float)):
        expected_price_variants.add(str(int(price_value)))
    expected_platform = str(SAMPLE_ITEM["platform"]).lower()

    assert any(
        f"${price}" in caption or price in caption
        for price in expected_price_variants
    )
    assert expected_platform in caption.lower()


def test_create_fit_card_with_empty_outfit_returns_fallback_message():
    caption = create_fit_card("   ", SAMPLE_ITEM)

    assert isinstance(caption, str)
    assert "could not be created" in caption.lower()
    assert "no outfit suggestion was available" in caption.lower()


# Groq-backed live integration checks.
def test_groq_live_search_listings_direct_call_returns_sensible_output():
    results = search_listings("vintage graphic tee", size="M", max_price=30)

    assert isinstance(results, list)
    assert len(results) > 0
    assert all(isinstance(item, dict) for item in results)


def test_groq_live_search_listings_no_results_is_empty_list_per_planning_spec():
    results = search_listings("diamond-encrusted space tuxedo", size="XXS", max_price=1)

    assert isinstance(results, list)
    assert results == []


def test_groq_live_suggest_outfit_with_wardrobe_direct_call_returns_text():
    _require_groq_key()

    result = suggest_outfit(SAMPLE_ITEM, SAMPLE_WARDROBE)

    assert isinstance(result, str)
    assert result.strip() != ""
    assert len(result.strip()) >= 20


def test_groq_live_suggest_outfit_empty_wardrobe_returns_informative_message():
    _require_groq_key()

    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())

    assert isinstance(result, str)
    assert result.strip() != ""
    lower = result.lower()
    assert any(word in lower for word in ["pair", "style", "wear", "shoes", "layer", "accessories"])


def test_groq_live_create_fit_card_direct_call_returns_caption_text():
    _require_groq_key()

    outfit = (
        "Pair the faded band tee with baggy dark-wash jeans and chunky white sneakers. "
        "Add a light bomber jacket for a relaxed 90s streetwear vibe."
    )
    caption = create_fit_card(outfit, SAMPLE_ITEM)

    assert isinstance(caption, str)
    assert caption.strip() != ""


def test_groq_live_create_fit_card_incomplete_outfit_returns_specific_message():
    caption = create_fit_card("   ", SAMPLE_ITEM)

    assert isinstance(caption, str)
    assert "could not be created" in caption.lower()
    assert "no outfit suggestion was available" in caption.lower()