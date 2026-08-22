# Pricing History — Klaviyo Connector

## 2026-08-22 — повторное подтверждение цены (suspend → update_pricing → deploy → submit_for_review)

Тот же паттерн, что и на Salesforce/HubSpot/Webflow/MuleSoft в этой же
сессии: `suspend_app` (было live) → первый `update_pricing` вернул
`'connect_klaviyo'/'disconnect_klaviyo'/'get_klaviyo_connection'
unexpectedly still priced` (расхождение только по free_tools) →
немедленный повтор с тем же payload прошёл без ошибки. Задокументировано
как задача #2275. `deploy_app` вернул 17/20 (ниже, чем у остальных
коннекторов в этой партии, но тот же класс "warning", не "error" —
локальный `imperal validate` при этом дал 0 проблем). `submit_for_review`
→ `pending_review`.

Обязательный журнал: каждое выставление или изменение цен на функции этого
приложения фиксируется здесь — что изменилось, почему, и на основании
чего. Не переписывать прошлые записи — только дописывать новые сверху.

---

## 2026-08-21 — Первичное выставление цен (до подачи на ревью)

**Порядок соблюдён по канону:** код готов → пост-аудит чистый (см.
`POST_AUDIT_LOG.md`, 6 найденных и исправленных багов) → `deploy_app` →
`update_pricing` → (далее) `submit_for_review`. Прайсинг выставлен ДО
ревью, как того требует `PRICING_POLICY.md` §1 — этот же файл был
переформулирован именно из-за инцидента с MuleSoft Connector, чтобы
больше не повторять ошибку.

**Метод — `developer.update_pricing`** (подтверждённо рабочий метод, тот
же, что MuleSoft Connector 2026-08-20). `pricing_config` передан как
настоящий JSON-объект (не строка). `revenue_split_dev=95` передан явным
параметром — partner-тир этого разработчика (подтверждён в ответе
`create_app`).

**Цены — фиксированная шкала `{0, 8, 16, 20, 40, 60}` из
`PRICING_POLICY.md` §2, применена по тому же принципу, что MuleSoft:**

| Уровень | Цена | Функции |
|---|---|---|
| Бесплатно (connect/status) | 0 | `connect_klaviyo`, `disconnect_klaviyo`, `get_klaviyo_connection` |
| Простое чтение (get/list) | 8 | `get_klaviyo_account`, все `list_*`/`get_*` (профили, списки, сегменты, события, метрики, кампании, флоу, шаблоны, теги, каталог, купоны, вебхуки) — 27 функций |
| Запись/мутация (create/update/delete/add/remove/tag) | 16 | `create_*`, `update_*`, `delete_*`, `add_profiles_to_list`, `remove_profiles_from_list`, `set_flow_status`, `tag_resource` — 20 функций |
| Необратимая рассылка реальным людям | 20 | `send_campaign` — единственная функция, которая фактически отправляет письмо/SMS живым контактам, поставлена на ступень выше обычной записи |

Разница с MuleSoft: там были отдельные тиры 40/60 для аудитов и bulk-
операций (`audit_cloudhub_environment`, `bulk_*`). У Klaviyo нет
собственных bulk/audit-инструментов в этом первом заходе — поэтому шкала
останавливается на 20 (`send_campaign`) как максимум, без искусственного
подтягивания цены туда, где нет reального дополнительного риска/веса.
Если в будущем добавятся audit/bulk-функции — использовать 40/60 по той
же логике.

**Итог:** `tool_prices` на все 50 функций сохранены в `tool-prices.json` и
зеркалированы в `imperal.json["pricing"]`. Известный read-back баг
платформы (см. `Docs/imperal-platform-issues.md`) означает, что ни один
инструмент чтения не подтверждает сохранённые цены напрямую — то же
ограничение, что документировано для MuleSoft.
