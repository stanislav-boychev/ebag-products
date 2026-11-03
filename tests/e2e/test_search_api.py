"""GET /products/search through the whole app: routing, validation, service, Postgres, JSON."""


def test_search_by_text(client, catalog):
    response = client.get("/products/search", params={"q": "yogurt"})

    assert response.status_code == 200
    body = response.json()
    assert [product["sku"] for product in body["items"]] == ["yogh-400"]
    assert (body["total"], body["page"], body["page_size"]) == (1, 1, 20)


def test_search_with_category_and_price_filters(client, catalog):
    response = client.get(
        "/products/search", params={"category_id": catalog["food"], "currency": "EUR", "max_price": 300}
    )

    assert response.status_code == 200
    assert [product["sku"] for product in response.json()["items"]] == ["milk-001"]


def test_upside_down_price_range_is_422(client, catalog):
    response = client.get("/products/search", params={"currency": "EUR", "min_price": 600, "max_price": 100})
    assert response.status_code == 422


def test_unknown_category_finds_nothing(client, catalog):
    response = client.get("/products/search", params={"category_id": 999})
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_unknown_parameter_is_422(client, catalog):
    response = client.get("/products/search", params={"currency": "EUR", "max_prise": 100})
    assert response.status_code == 422
