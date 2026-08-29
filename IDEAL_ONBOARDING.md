# Klaviyo Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: email/SMS-
маркетолог e-commerce бренда на Klaviyo (часто в связке с Shopify).

## 1. Credential type
API key (private key, одно поле).

## 2. Идеальный флоу
1. **Первое открытие** — `Empty` со ссылкой "Settings > API Keys > Create Private API
   Key" + список нужных scopes (Campaigns, Flows, Profiles, Lists read/write).
2. **Форма** — api_key (password-type) с лейблом.
3. **После успеха** — сводка: активные flows (сколько сообщений отправлено сегодня),
   размер листов/сегментов, последние campaigns — сразу, максимально знакомо для
   email-маркетолога (похоже на их родной дашборд Klaviyo).
4. **Shopify cross-app awareness** — идеально: если у пользователя уже подключен Shopify
   Connector — явная подсказка "мы видим, что у вас подключен Shopify — синхронизация
   каталога товаров для Klaviyo доступна" (межприложенческий момент открытия ценности).
5. **Ошибка "rate limited"** — Klaviyo API строго лимитирует по burst — конкретное
   сообщение с реальным Retry-After, если приходит.

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0.
