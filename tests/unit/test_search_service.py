"""The search service, called directly, without HTTP. It runs its queries on real Postgres."""

import pytest
from pydantic import ValidationError
from sqlalchemy import func, update

from app.db.models import Product
from app.schemas import MAX_ID, SearchParams
from app.services.search import search_products


def search(session, **filters):
    """Run the service and return the SKUs found, in order."""
    return [product.sku for product in search_products(session, SearchParams(**filters))["items"]]


def test_no_filters_returns_everything_in_id_order(session, catalog):
    assert search(session) == ["milk-001", "yogh-400", "chee-200", "watr-015", "natu-001"]


def test_deleted_products_are_not_found(session, catalog):
    session.execute(update(Product).where(Product.sku == "milk-001").values(deleted_at=func.now()))
    session.commit()
    assert search(session, sku="milk-001") == []
    assert search(session, q="milk") == ["natu-001"]


def test_q_matches_title_ignoring_case(session, catalog):
    assert search(session, q="MILK") == ["milk-001", "natu-001"]


def test_q_does_not_match_sku(session, catalog):
    assert search(session, q="milk-001") == []


def test_sku_matches_ignoring_case(session, catalog):
    assert search(session, sku="CHEE-200") == ["chee-200"]


def test_sku_must_match_whole_sku(session, catalog):
    assert search(session, sku="chee-2000") == []


def test_q_treats_percent_literally(session, catalog):
    assert search(session, q="00%") == ["natu-001"]


def test_q_treats_underscore_literally(session, catalog):
    assert search(session, q="m_l") == []


def test_price_range_is_inclusive(session, catalog):
    assert search(session, currency="EUR", min_price=249, max_price=599) == ["milk-001", "yogh-400", "chee-200"]


def test_currency_filter(session, catalog):
    session.add(Product(sku="milk-usd", title="US milk", price=300, currency="USD", category_id=catalog["dairy"]))
    session.commit()
    assert search(session, currency="USD") == ["milk-usd"]
    assert search(session, currency="USD", max_price=300) == ["milk-usd"]
    assert search(session, currency="EUR", min_price=300, max_price=300) == []


def test_min_price_only(session, catalog):
    assert search(session, currency="EUR", min_price=500) == ["chee-200"]


def test_max_price_only(session, catalog):
    assert search(session, currency="EUR", max_price=150) == ["watr-015", "natu-001"]


def test_category_includes_all_subcategories(session, catalog):
    assert search(session, category_id=catalog["food"]) == ["milk-001", "yogh-400", "chee-200"]


def test_category_without_subcategories(session, catalog):
    assert search(session, category_id=catalog["cheese"]) == ["chee-200"]


def test_unknown_category_finds_nothing(session, catalog):
    assert search(session, category_id=999) == []


def test_filters_are_combined(session, catalog):
    assert search(session, q="milk", category_id=catalog["drinks"]) == ["natu-001"]
    assert search(session, q="milk", currency="EUR", max_price=200) == ["natu-001"]
    assert search(session, sku="milk-001", category_id=catalog["drinks"]) == []


def test_page_and_page_size(session, catalog):
    assert search(session, page_size=2) == ["milk-001", "yogh-400"]
    assert search(session, page=2, page_size=2) == ["chee-200", "watr-015"]
    assert search(session, page=4, page_size=2) == []


def test_total_counts_all_matches_not_just_the_page(session, catalog):
    result = search_products(session, SearchParams(q="milk", page_size=1))
    assert len(result["items"]) == 1
    assert result["total"] == 2


@pytest.mark.parametrize(
    "params",
    [
        {"currency": "EUR", "min_price": 600, "max_price": 100},  # range upside down
        {"currency": "EUR", "min_price": -1},
        {"currency": "EUR", "max_price": 10**30},  # above the 100,000 maximum
        {"min_price": 100},  # amounts in different currencies can't be compared
        {"max_price": 100},
        {"currency": "CHF"},
        {"category_id": 0},
        {"category_id": MAX_ID + 1},
        {"q": ""},
        {"q": "ab"},  # below the 3-character minimum
        {"q": " ab "},
        {"q": "   "},  # only spaces
        {"q": "a\x00b"},  # NUL bytes are not allowed
        {"sku": "milk-01"},  # below the 8-character minimum
        {"sku": "milk 0001"},  # spaces are not allowed
        {"page": 0},
        {"page": 101},
        {"page_size": 0},
        {"page_size": 101},
    ],
)
def test_invalid_parameters_are_rejected(session, params):
    with pytest.raises(ValidationError):
        search(session, **params)


def test_q_has_surrounding_spaces_removed(session, catalog):
    assert search(session, q="  yogurt ") == ["yogh-400"]


def test_values_sent_as_text_are_converted(session, catalog):
    assert search(session, currency="EUR", min_price="500") == ["chee-200"]


def test_page_defaults(session):
    result = search_products(session, SearchParams())
    assert (result["page"], result["page_size"]) == (1, 20)
