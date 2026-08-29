# Klaviyo Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `klaviyo-connector`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Column`(align="start") + `ui.Text`(account) + `ui.Divider` + navigation `ui.ListItem`(Lists/Campaigns/Flows/Segments) + `ui.Button`("App settings") | Без карточек по стандарту. |
| Campaigns Dashboard (center, `center_overlay=True`) | `ui.Stats`(Sent today/Open rate/Click rate) + `ui.DataTable`(campaign, channel Badge email/SMS, status, sent date, open rate; sortable) | `DataTable` — стандартный способ работы со списком кампаний с числовыми метриками в колонках. |
| Campaign Detail | Back-button + `ui.KeyValue`(subject/audience/send time) + `ui.Chart`(type="bar" — opens/clicks/unsubscribes) + `ui.RichEditor`(content, read-only preview письма) | `RichEditor` — единственный примитив с рендерингом HTML-контента (используется тут в режиме просмотра готового письма). |
| Flow Builder Overview | `ui.List`(flows: name, trigger, status Badge live/draft/paused) | Список автоматизаций с их статусом — обычный List, без декоративных карточек. |
| Segment/List Viewer | `ui.DataTable`(profiles: email, name, last active; sortable) + `ui.Input`(param_name="query", placeholder="Найти по email...", on_submit=Call) | Поиск профиля внутри списка/сегмента через простой Input + Call. |
| Profile Detail | `ui.KeyValue`(email/phone/location) + `ui.TagInput`(applied tags/segments membership, read-only отображение) + `ui.Timeline`(events: Placed Order, Viewed Product, Opened Email) | `Timeline` идеально ложится на событийную историю профиля Klaviyo. |
| Catalog (products) | `ui.DataTable`(image thumb via `ui.Image`, title, price, published Badge) | Каталог товаров для персонализированных блоков в письмах. |
| Coupon Manager | `ui.List`(coupons) + `ui.Button`("Создать код") + `ui.Dialog`(создание: `ui.Input`(prefix)+`ui.Input`(type="number", count)) | Создание пачки кодов — деструктивно необратимо (коды расходуются), не критично для confirm, но форма в Dialog держит поток компактным. |
| App Settings | `ui.Accordion`([Connections+Disconnect, Webhooks CRUD, Default List Select]) | Централизованные настройки по стандарту. |

## 2. User flow (валидно по panel lifecycle)

1. **SESSION INIT** → `__panel__klaviyo_sidebar` рендерит account + разделы;
   `auto_action` открывает Campaigns Dashboard, если `not active_view`.
2. Campaigns Dashboard: DataTable → клик на строку (`on_row_click`) →
   `ui.Call("__panel__klaviyo_center", campaign_id=...)` → Campaign Detail
   (KeyValue + Chart + RichEditor preview).
3. Раздел "Lists/Segments" → Segment Viewer (DataTable профилей) → клик на профиль →
   `ui.Call(profile_id=...)` → Profile Detail (Timeline событий).
4. Раздел "Flows" → List автоматизаций → клик на флоу → тот же паттерн детали
   (KeyValue триггера + Chart конверсии по шагам).
5. Действие "Создать код" в Coupon Manager → Dialog с формой → `create_coupon_code`
   → `refresh_panels=["klaviyo_coupons"]`.
6. "App settings" → отдельный center overlay с Accordion-секциями.

## 3. Конкретные экраны (screens)

### Screen: Campaigns Dashboard (`klaviyo_center`, default)
- Stats row: Sent today / Open rate / Click rate.
- DataTable: campaign, channel Badge, status, sent date, open rate — row-click →
  Campaign Detail.

### Screen: Campaign Detail (`klaviyo_center` + `campaign_id`)
- Back-button "← К кампаниям".
- KeyValue: subject, audience, send time.
- Chart (bar): opens/clicks/unsubscribes.
- RichEditor (read-only): превью письма.

### Screen: Segment/List Viewer (`klaviyo_segments` + `segment_id`)
- Input(поиск по email, on_submit=Call) сверху.
- DataTable: email, name, last active — row-click → Profile Detail.

### Screen: Profile Detail (`klaviyo_segments` + `profile_id`)
- Back-button "← К списку".
- KeyValue: email, phone, location.
- TagInput (read-only): сегменты, в которых состоит профиль.
- Timeline: события (Placed Order, Viewed Product, Opened Email).

### Screen: App settings (`klaviyo_settings`)
- Accordion "Подключение": API key info, Disconnect (Dialog-подтверждение).
- Accordion "Список по умолчанию": Select.
- Accordion "Webhooks": List + Button "Добавить".
