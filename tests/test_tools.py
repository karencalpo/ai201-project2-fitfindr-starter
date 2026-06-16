from tools import search_listings


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