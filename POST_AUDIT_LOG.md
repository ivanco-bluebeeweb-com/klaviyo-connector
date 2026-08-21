# Post-Audit Log — Klaviyo Connector

Формат и правила ведения: см. `/Users/vladivanco/Documents/Imperal OS/POST_AUDIT_LOG_STANDARD.md`.
Новые записи добавляются СВЕРХУ.

---

## 2026-08-21 — Сквозной пост-аудит (первичная разработка)

**Что проверялось:** py_compile/AST всех модулей; `imperal.json` ↔ число
`@chat.function` (50, совпадает); каждый `kc.<method>(...)` вызов против
реально определённых функций в `klaviyo_client.py`; каждый конструктор
SDL-модели (`Profile(...)`, `Template(...)` и т.д.) против реально
объявленных полей; сигнатуры `_get_key`/`_need_key` против реального
async-контракта `ctx.secrets.get()`; полный прогон pytest.

**Метод:** написание собственного AST-скрипта, сравнивающего все
`kc.xxx(...)` вызовы в 5 handler-файлах с реальными top-level функциями
`klaviyo_client.py`, и все конструкторы `SomeModel(field=...)` с реально
объявленными `AnnAssign`-полями в `models.py`; параллельно — написание
63 pytest-тестов по каждому из 50 `@chat.function`, что на практике
исполнило каждую строчку кода хотя бы одним реальным вызовом с mock HTTP.

**Почему именно так:** ни `imperal validate`, ни `ast.parse` не ловят
опечатки в именах методов клиента, несуществующие поля Pydantic-моделей,
или async/sync путаницу — они видны только при реальном исполнении. Раз
статическая валидация была уже чистой (0 errors), риск в том, что
приложение выглядит готовым, но падает на первом реальном вызове.

### Находки

1. **`accounts.py::_get_key`** была объявлена `async def`, но тело
   вызывало `ctx.secrets.get(...)` без `await` — на реальном SDK это
   корутина, поэтому `_get_key` **всегда** возвращала truthy
   coroutine-объект вместо реального значения (или его отсутствия),
   полностью ломая проверку "подключён ли Klaviyo" во всём приложении
   (ни одна `_need_key`-проверка никогда не сработала бы).
2. **`_need_key` в 4 handler-файлах** (`handlers_profiles.py`,
   `handlers_events.py`, `handlers_campaigns.py`, `handlers_catalog.py`)
   были синхронными, вызывающими синхронную (тогда ещё не исправленную)
   `_get_key` без `await` — тот же класс бага, размноженный по 46 сайтам
   вызова.
3. **`klaviyo_client.request()`** изначально была `def` (не `async def`),
   реализована через блокирующий `httpx.request` + `time.sleep`, но
   вызывалась `await kc.request(...)` в 48 местах — рабочий код, потому
   что `await` на не-корутине с `__await__` падает, но архитектурно
   неверно и блокировало бы event loop на каждом вызове. Исправлено на
   `ctx.http.<method>(...)` (платформенный HTTP-клиент, mockable в тестах),
   тем же паттерном, что документирует DataForSEO Connector в `dfs_client.py`.
4. **`handlers_campaigns.py` (×3) и `handlers_catalog.py` (×4)** вызывали
   `kc.extract_next_cursor(payload)` — функция с таким именем никогда не
   существовала в `klaviyo_client.py` (реальное имя —
   `next_cursor_from_links`). `AttributeError` на первом же вызове любой
   из 7 пагинированных list-функций в этих двух доменах.
5. **`create_campaign`** ссылалась на `params.list_or_segment_ids` и
   `params.preview_text` — оба поля не существуют на
   `CreateCampaignParams` (реальные поля: `list_ids`, `segment_ids`, без
   `preview_text`). `AttributeError` на каждом вызове.
6. **`_template_from_row`** конструировала `Template(..., editor_type=...)`
   — `Template` не объявляет `editor_type`. Pydantic отклонил бы это как
   лишнее поле (`ValidationError`) на каждом вызове `list_templates`/
   `get_template`/`create_template`.
7. **`_profile_from_row`** конструировала `Profile(..., properties=...)`
   — `Profile` не объявляла `properties`. Тот же класс `ValidationError`
   на каждом вызове `create_profile`/`get_profile`/`list_profiles`/etc.
8. **`list_campaigns`/`list_flows`/`list_templates`** читали
   `params.page_size`, но `ListCampaignsParams`/`ListFlowsParams`/
   `ListTemplatesParams` не объявляли это поле (в отличие от параллельной
   `ListMembersParams`, которая его объявляет) — `AttributeError`.
9. **`panels.py`** (`_quick_counts`, `klaviyo_overview_panel`) вызывали
   `_get_key(ctx)` синхронно и `kc.request(key, ...)` со старой
   (до-ctx) сигнатурой — не покрыто pytest (панели не юнит-тестируются
   тем же способом), поймано только ручным чтением после фикса №3.
10. **`app.py::health_check`** вызывал `ctx.secrets.get(...)` без
    `await` — корутина создавалась и никогда не ожидалась, health-check
    не выполнял реальную проверку (хотя и не падал явно).

### Исправления

- `_get_key` → `await ctx.secrets.get(...)`, с комментарием почему.
- `_need_key` в 4 файлах → `async def`, `await _get_key(ctx)`; все 46
  сайтов вызова → `await _need_key(ctx)`.
- `klaviyo_client.request(ctx, api_key, method, path, ...)` → делегирует
  на `ctx.http.<method>(...)`, убран `httpx`/`time` импорт, добавлен
  `asyncio.sleep` для retry-backoff. Все 48 сайтов вызова получили `ctx`
  первым аргументом.
- `kc.extract_next_cursor` → `kc.next_cursor_from_links` (7 сайтов,
  `sed`-замена, проверено grep'ом на 0 остатков).
- `create_campaign` переписана на реальные поля модели
  (`list_ids + segment_ids`, без `preview_text`).
- `Template`/`_template_from_row` — убрано `editor_type` (поле не
  добавлено в модель, т.к. Klaviyo API templates не отдаёт такое поле
  в `attributes` — было ошибочно придумано, не документировано).
- `Profile` — добавлено `properties: dict = Field(default_factory=dict)`
  (поле осмысленное — сериализованные custom-свойства контакта, оставлено
  в модели, а не убрано из хендлера).
- `ListCampaignsParams`/`ListFlowsParams`/`ListTemplatesParams` — добавлено
  `page_size: int = Field(20, ge=1, le=100)` для консистентности с
  `ListMembersParams`.
- `panels.py` — оба места переведены на `await _get_key(ctx)` и
  `kc.request(ctx, key, ...)`.
- `app.py::health_check` — `await ctx.secrets.get(...)`.

### Результат проверки после исправлений

`imperal validate .` → 0 errors, 0 warnings. `imperal build .` → манифест
пересобран, 50 tools. Полный `pytest tests/` → **63/63 passed** (5 файлов,
покрывающих все 50 `@chat.function`: accounts, profiles/lists/segments,
events/metrics, campaigns/flows/templates/tags, catalog/coupons/webhooks).
Автоматический AST-скрипт повторно прогнан после всех фиксов — 0 плохих
`kc.*` вызовов, 0 несоответствий конструктор↔модель, 0 отсутствующих
импортов.

**Статус: FIXED**

---

## Известный нерешённый блокер (не баг в коде)

`icon.svg` — упрощённый геометрический placeholder (монограмма "K"), НЕ
официальный логотип Klaviyo. Официальные бренд-ассеты Klaviyo закрыты за
Partner Portal (тот же паттерн, что и у UiPath/Automation
Anywhere/Blue Prism/MuleSoft Connector в этом портфеле — см. их
`icon.svg`). Приложение НЕ публиковалось по этой причине — см. Vikunja
#2191 для полного описания блокера и текущего статуса.
