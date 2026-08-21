# Klaviyo Connector — Connector Discovery

Метод: `Docs/session-notes/CONNECTOR_DISCOVERY_STANDARD.md`.

## 1. Целевой сервис и источники

Klaviyo — email/SMS marketing automation platform (BYOK, private API key).

Официальные источники (проверено 2026-08-20):
- `developers.klaviyo.com/en/reference/api_overview` — полный API reference.
- `developers.klaviyo.com/en/docs/authenticate_requests` — auth scheme
  (`Authorization: Klaviyo-API-Key <key>`, не Bearer/OAuth для private keys).
- `developers.klaviyo.com/en/docs/api_versioning_and_deprecation_policy` —
  обязательный `revision` header.
- `developers.klaviyo.com/en/docs/rate_limits_and_error_handling` —
  двухоконный fixed-window rate limit (burst 1s / steady 60s), 5 весовых
  тиров (XS/S/M/L/XL) для разных endpoints, `Retry-After` header.
- `developers.klaviyo.com/en/reference/jsonapi` — JSON:API pagination/filter
  conventions (`page[cursor]`, `filter=equals(...)`, sparse fieldsets).

## 2. Карта возможностей (направление на каждую)

| Возможность | Ingress/Egress/Both | Комментарий |
|---|---|---|
| Profiles CRUD | Both | Person record — email/phone/external_id identified |
| Lists CRUD + membership | Both | Static opt-in groups |
| Segments (read + membership read) | Ingress | Klaviyo-computed dynamic groups — no direct write API |
| Events (create) + Metrics (list) | Egress/Ingress | Behavioral data layer |
| Campaigns CRUD + send | Both | One-off email/SMS sends |
| Flows (list/get/set status) | Both | Automated multi-step sequences — status toggle only, flow logic itself is UI-authored |
| Templates CRUD | Both | Reusable HTML email bodies |
| Tags (create/list/attach) | Both | Organizing labels across campaigns/flows/lists/segments |
| Catalog Items/Categories CRUD | Both | Product data for dynamic email/SMS blocks |
| Coupons + Coupon Codes | Both | Discount codes for flows/campaigns |
| Webhooks CRUD + topic list | Both | Outbound HTTP notifications on Klaviyo-side events |
| Data Privacy Deletion Jobs | Egress | GDPR/CCPA profile deletion requests |

## 3. Ярус 1 — Ключевые функции (P0-кандидаты)

connect/disconnect/get_connection, create/get/update/delete profile,
create/get/list lists, add/remove profiles to/from list, create event,
list campaigns, create campaign, send campaign.

## 4. Ярус 2 — Полное покрытие

Все 50 реализованных функций — `included`:

Accounts (4): connect_klaviyo, disconnect_klaviyo, get_klaviyo_connection,
get_klaviyo_account.

Profiles/Lists/Segments (19): create/update/get/list/delete_profile,
request_profile_deletion, create/list/get/delete_list,
add/remove_profiles_to/from_list, list_list_members,
list/get_segment, list_segment_members.

Events/Metrics (3): create_event, list_events, list_metrics.

Campaigns/Flows/Templates/Tags (16): list/get/create/send_campaign,
list/get/set_flow_status, list/get/create_template,
list/create_tag, tag_resource.

Catalog/Coupons/Webhooks (16): list/get/create/update/delete_catalog_item,
list_catalog_categories, list/create/delete_coupon,
list/create_coupon_code, list_webhook_topics,
list/create/delete_webhook.

`deferred`: OAuth partner-app auth model (only relevant if Imperal itself
becomes a listed Klaviyo partner app — different, later product decision).
`not applicable`: Klaviyo's visual flow-editor / email-template drag-drop
builder — no API surface, UI-only in Klaviyo itself.

## 5. Ярус 3 — Функции на нашей стороне (value-add)

- Единый `klaviyo_client.request()` с централизованной 429-retry логикой
  (два одновременных rate-limit окна Klaviyo, honoring `Retry-After`) —
  каждый handler получает это бесплатно вместо реализации самостоятельно.
- `connect_klaviyo` валидирует ключ перед сохранением (1 дешёвый GET),
  вместо тихого падения при первом реальном вызове.
- Единая панель обзора аккаунта (`klaviyo_overview_panel`) с быстрыми
  счётчиками Profiles/Lists/Segments/Campaigns/Flows — Klaviyo API этого
  агрегата не отдаёт одним вызовом.

## 6. Решение по объёму этого захода

Разработчик (Влад) заявил объём **до начала работы над этим коннектором**:
"приступай к разработке приложения Klaviyo. максимальный функционал,
полный максимум" — прямая цитата из первого сообщения по этому коннектору.
Это действует как уже данный ответ по Шагу 5 стандарта (Ярус 1 + Ярус 2 +
Ярус 3) — повторный вопрос не задавался, разработка сразу пошла в Фазу 3
(Дизайн/код) на полном объёме.

Подтверждено: 2026-08-20/21, полное покрытие (50 функций) реализовано и
протестировано (63/63 pytest, 0 ошибок валидации).
