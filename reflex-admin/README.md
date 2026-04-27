# reflex-admin

A Reflex port of the react-admin "Posters Galore" demo, built for the browser-vs-API agent benchmark in this repo's root.

## Layout

```
reflex_admin/
├── reflex_admin.py      app + page routes
├── state.py             Reflex State — UI handlers (also exposed as HTTP endpoints by the plugin)
├── layout.py            sidebar + page chrome
├── data.py              in-memory datastore loaded from ../seed.json
└── pages/
    ├── customers.py
    ├── orders.py
    └── reviews.py
```

## How the API is generated

`rxe.EventHandlerAPIPlugin` (configured in `rxconfig.py`) auto-generates an HTTP endpoint for **every** event handler on the State — `set_customers_query`, `load_order`, `accept_review`, etc. There is no API-specific code in `state.py`; the same handlers that drive the UI also serve the API.

The plugin requires `reflex-enterprise`; the app uses `rxe.App()` and `rxe.Config()` instead of `rx.App()` / `rx.Config()`. Responses stream as NDJSON state deltas — including recomputed dependent computed vars (`customer_rows`, `order_rows`, `review_rows`, `selected_order`, `selected_customer_orders`, etc.). The agent reads those vars from the delta stream rather than from a dedicated response payload.

## Running

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
reflex login                # one-time, for reflex-enterprise
reflex init
reflex run
```

- Frontend: http://localhost:3001
- API: http://localhost:8001/_reflex/event/...
- OpenAPI spec: http://localhost:8001/_reflex/events/openapi.yaml

## Endpoints

All endpoints are `POST` to `/_reflex/event/<state_path>/<handler>` with a JSON body of args and an `Authorization: Bearer <uuid>` header. The state path here is `reflex_admin___state____state`. The plugin also adds `POST /_reflex/retrieve_state` (full session state dump) and `GET /_reflex/events/openapi.yaml`.

The agent's REST-shaped tool surface (`list_customers`, `update_order`, etc.) is mapped in `run_api_agent.py` to handler sequences:

| Tool | Handler sequence | Read from delta |
| --- | --- | --- |
| `list_customers(q)` | `set_customers_query(q)` | `customer_rows` |
| `list_orders(customer_id)` | `load_customer(customer_id)` | `selected_customer_orders` |
| `list_orders(status)` | `set_orders_tab(status)` | `order_rows` |
| `update_order(id, status)` | `load_order` → `set_order_status_draft` → `save_order_status` | `selected_order` |
| `list_reviews(status)` | `set_reviews_status_filter(status)` | `review_rows` |
| `update_review(id, accepted)` | `select_review` → `accept_review` → `select_review` | `selected_review` |
| `update_review(id, rejected)` | `select_review` → `reject_review` → `select_review` | `selected_review` |

Multi-step flows mirror the UI: marking an order delivered is the same load-edit-save sequence the order detail page uses.
