import os
import pytest
from tools import search_listings, suggest_outfit


SAMPLE_ITEM = {
    "title": "Faded Band Tee",
    "category": "tops",
    "colors": ["black", "grey"],
    "style_tags": ["vintage", "graphic", "oversized"],
    "description": "Worn-in band tee with a faded print.",
    "price": 22,
    "platform": "Depop",
}

SAMPLE_WARDROBE = {
    "items": [
        {
            "id": "w_001",
            "name": "Baggy straight-leg jeans, dark wash",
            "category": "bottoms",
            "colors": ["dark blue", "indigo"],
            "style_tags": ["denim", "streetwear", "baggy"],
            "notes": "High-waisted, sits above the hip",
        },
        {
            "id": "w_002",
            "name": "White ribbed tank top",
            "category": "tops",
            "colors": ["white"],
            "style_tags": ["basics", "minimal", "fitted"],
            "notes": "Goes with everything",
        },
        {
            "id": "w_003",
            "name": "Chunky platform sneakers",
            "category": "shoes",
            "colors": ["white"],
            "style_tags": ["streetwear", "chunky"],
            "notes": None,
        },
    ]
}


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


def test_search_listings_no_matches_returns_empty_list():
    results = search_listings("diamond-encrusted space tuxedo", size="XXS", max_price=1)

    assert results == []


def _skip_if_no_groq_key():
    if not os.environ.get("GROQ_API_KEY"):
        pytest.skip("GROQ_API_KEY is not set; skipping live suggest_outfit tests.")


def test_suggest_outfit_with_wardrobe_returns_nonempty_styling_text():
    _skip_if_no_groq_key()

    result = suggest_outfit(SAMPLE_ITEM, SAMPLE_WARDROBE)

    assert isinstance(result, str)
    assert result.strip() != ""
    assert len(result.strip()) >= 20


def test_suggest_outfit_with_empty_wardrobe_returns_general_advice():
    _skip_if_no_groq_key()

    result = suggest_outfit(SAMPLE_ITEM, {"items": []})
    lower = result.lower()

    assert isinstance(result, str)
    assert result.strip() != ""
    assert any(
        word in lower
        for word in ["pair", "style", "wear", "shoes", "accessories", "layer"]
    )


def test_suggest_outfit_handles_missing_items_key_gracefully():
    _skip_if_no_groq_key()

    result = suggest_outfit(SAMPLE_ITEM, {})

    assert isinstance(result, str)
    assert result.strip() != ""