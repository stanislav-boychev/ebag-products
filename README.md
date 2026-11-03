# Catalogue service

A service for products and categories in an e-commerce system: FastAPI, SQLAlchemy 2, Pydantic,
Alembic and Postgres.

CRUD for products and categories, a search endpoint, and tests for search (unit and API).

## Quick start

Requires Docker with Compose v2 (running), [uv](https://docs.astral.sh/uv/) and make. uv installs Python 3.13 if missing. Ports 5433 and 8000 must be free.

```bash
cp .env.example .env
make db        # Postgres 17 on localhost:5433
make install
make migrate
make run       # http://localhost:8000/docs
```

`make run` reloads on file changes. `make db-stop` stops Postgres and keeps the data. `make db-reset` deletes all data; run `make migrate` after it. `make psql` opens a SQL shell.

`DATABASE_URL` comes from the environment or `.env`; it has no default; without it, the first database call (or `make migrate`) fails.

## API

Full reference, with every field and limit: http://localhost:8000/docs (while the app is running).

| Method | Path | Does |
|---|---|---|
| GET | `/categories` | List categories, paged, ordered by id |
| POST | `/categories` | Create |
| GET | `/categories/{id}` | Get one |
| PUT | `/categories/{id}` | Replace |
| DELETE | `/categories/{id}` | Soft delete; 409 if it still has subcategories or products |
| GET | `/products` | List products, paged, ordered by id |
| POST | `/products` | Create |
| GET | `/products/{id}` | Get one |
| PUT | `/products/{id}` | Replace |
| DELETE | `/products/{id}` | Soft delete |
| GET | `/products/search` | Search and filter products (below) |
| GET | `/health` | 200 if the service can reach the database, 503 if it can't |

Errors: 404 for an unknown id; 422 for invalid input (including an unknown field or query parameter), an unknown
`category_id` or `parent_id`, or a category moved under its own subcategory; 409 for a duplicate SKU or category
name, or deleting a category in use.

### Search

`GET /products/search` takes any combination of these query parameters, combined with AND:

| Parameter | Matches |
|---|---|
| `q` | At least 3 characters. Title contains it, case-insensitive. `%` and `_` are matched literally. |
| `sku` | The whole SKU, case-insensitive. Same format as on products, so 8–64 characters. |
| `category_id` | Products in that category or any of its subcategories. An unknown category finds nothing. |
| `currency` | Products in that currency. Required with `min_price` or `max_price`. |
| `min_price`, `max_price` | Price in cents, inclusive. 422 if `min_price` > `max_price`. |
| `page`, `page_size` | Paging: page 1–100, default 1; page size 1–100, default 20. |

Results are ordered by id. Example: `/products/search?q=milk&category_id=1&currency=EUR&max_price=300`.

## Tests

```bash
make db         # tests need Postgres running
make test       # creates the products_test database if needed
```

- `tests/unit/` calls the search service, including its parameter rules, without HTTP.
- `tests/e2e/` calls `GET /products/search` through FastAPI's `TestClient`, covering the common cases.

Service tests use real Postgres, because the behaviour under test is the SQL (`ILIKE`, the recursive query);
a mock would prove nothing. Tests use a separate `products_test` database, built by the real migrations.
To use another database, set `TEST_DATABASE_URL` in the environment; it is not read from `.env`.

## Lint and format

`make lint` checks and `make fmt` formats, both with Ruff. CI runs lint, checks migrations match the models, and runs the tests against Postgres 17.

## Project layout

| Path | What it does |
|---|---|
| `app/main.py` | Creates the app, mounts the routers, maps service errors to status codes |
| `app/config.py` | Settings from environment variables (pydantic-settings) |
| `app/routers/` | HTTP handlers: parse the request, call a service, return the result |
| `app/schemas.py` | Request bodies (`*Write`, validated) and responses (`*Read`) with Pydantic |
| `app/services/` | Categories, products and search: the logic and database queries; know nothing about HTTP |
| `app/db/models.py` | Tables (SQLAlchemy ORM) |
| `app/db/session.py` | Engine (connection pool), one session per request, `Base` for models |
| `app/exceptions.py` | `NotFound`, `InvalidInput`, `Conflict`, raised by the services |
| `alembic/versions/` | Migrations, one file per schema change |
| `tests/unit/`, `tests/e2e/` | Search tests; `conftest.py` holds the shared setup |

## Migrations

After changing `app/db/models.py`:

```bash
make migration m="add stock to products"
make migrate
```

Review the generated file before applying it: autogenerate misses renames, for example.

## Data model

```
categories                         products
----------                         --------
id          bigint PK              id           bigint PK
name        varchar(100), UNIQUE   sku          varchar(64), UNIQUE unless deleted
            unless deleted
parent_id   FK -> categories.id    title        varchar(200)
            NULL = top level       description  text, default ''
created_at  timestamptz            image_url    varchar(2083) NULL
updated_at  timestamptz            price        integer (cents), CHECK price >= 0
deleted_at  timestamptz NULL       currency     varchar(3), default 'EUR'
                                   category_id  FK -> categories.id, NOT NULL
                                   created_at, updated_at  timestamptz
                                   deleted_at   timestamptz NULL
```

Both foreign keys are indexed, and `title` has a trigram (`pg_trgm`) index for `ILIKE`.
Both tables soft delete through `deleted_at`, and neither delete cascades.

## Design decisions

| Decision | Choice | Why |
|---|---|---|
| Price type | Integer cents (`249` = 2.49), at most 100,000.00 in any currency | Money must be exact; integers can't round. The cap catches typos. |
| Currency | Stored on each product: EUR, USD or GBP. Each product has one price, with no conversion | Every price states its currency. Price filters need a `currency`, because 300 in one currency can't be compared with 300 in another. |
| Image | A URL, validated as http(s) | Uploads need storage, resizing and a CDN; a catalogue service usually just references them. |
| SKU | Unique; 8–64 letters, digits, `-`, `_`; stored in lowercase | `MILK-001` and `milk-001` should be one product. The minimum is our own policy, as no industry standard sets SKU length. |
| Product must have a category | Yes | Every product in a shop is browsable somewhere. |
| Deleting a category in use | Refused with 409 | Cascading would silently delete products. |
| Category cycles | Refused with 422 | A category under its own subcategory has no valid place in the tree. |
| Category names | Unique across all categories; stored in lowercase | A concept such as Organic exists once, as its own category, rather than being duplicated under several parents. Lowercase makes `Dairy` and `dairy` one name. |
| Updates | PUT (replace the whole object) | One body shape for create and update keeps the API and code simple. |
| Input | JSON integers must be real integers; titles and category names have surrounding spaces removed | `true` must not become a price of 1 cent, and a blank title isn't a title. |
| Pagination | `page` 1–100 and `page_size` 1–100, default 20: at most 10,000 rows reachable per query | Simple, and allows jumping to a page. Going through a whole larger catalogue would need keyset pagination. |
| Deletes | Soft delete with `deleted_at`, for products and categories | Orders will need to reference products that are no longer sold, along with their categories. |
| `q` and `sku` | Separate parameters: `q` searches the title text, `sku` is an exact filter like the others | A title is free text, and a SKU is an identifier. One `q` for both would mix two meanings with OR. Matching category names is a relevance feature and needs ranking. |
| Category filter | By `category_id`, including subcategories | Ids survive renames, and choosing a category should also show what sits below it. |
| SKU changes | Allowed through PUT, if still unique | Products are identified by `id`, so a correction breaks nothing here. Other systems may key on SKU, so production would need renames restricted or announced to them. |
| Search term length | `q` needs at least 3 characters | An `ILIKE` term under 3 characters gives no trigrams to look up, so Postgres scans the whole title index. They also match too much to be useful. |
| Integrity | Unique SKU and category name among non-deleted rows, foreign keys and `price >= 0` enforced by Postgres | The database is the last line of defence, whatever code writes to it. |
| Handlers | Sync `def` with sync SQLAlchemy | Queries are short and each needs a pooled connection either way, so async would add complexity without lifting that limit. |
| Auth | None | Out of scope; would sit in front (gateway) or as a dependency. |

## Known limitations

- Deleting a category reads its subcategories and products, then writes. A product or subcategory added in between would be left
  under a deleted category. Fixing it needs both sides to lock the category row: `FOR UPDATE` on delete and `FOR SHARE`
  on writers, because the foreign key check ignores `deleted_at`.
- The cycle check reads the tree, then writes. Two concurrent moves (A under B and B under A) could both
  pass. Fixing it needs a lock, e.g. `SELECT ... FOR UPDATE` on the rows involved, or a serializable transaction.
- Search has no relevance ranking or typo tolerance, and results are ordered by id. A search engine
  (OpenSearch) would add those, plus Bulgarian language analysis.
- No sort parameter yet: a price sort would need a currency and an id tiebreaker for stable pages.
- Image URLs are normalised by Pydantic: a bare host gains a trailing slash (`https://img.example.com/`).
