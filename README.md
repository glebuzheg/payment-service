# Асинхронный сервис платежей

FastAPI принимает платёж и сразу возвращает `202 Accepted`. Событие сохраняется в outbox вместе с платежом, затем публикуется в RabbitMQ. Один consumer эмулирует шлюз и отправляет результат по webhook.

## Запуск

Нужны Docker и Docker Compose.

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

API доступен на `http://localhost:8000`, документация — `/docs`, панель RabbitMQ — `http://localhost:15672` (`guest` / `guest`). Ключ в `.env.example` предназначен только для локальной проверки; перед публичным запуском замените его.

## Создать и получить платёж

```bash
set -a; . ./.env; set +a
curl -i -X POST http://localhost:8000/api/v1/payments \
  -H "X-API-Key: $API_KEY" \
  -H 'Idempotency-Key: order-42' \
  -H 'Content-Type: application/json' \
  -d '{"amount":"1250.00","currency":"RUB","description":"Заказ 42","metadata":{"order_id":42},"webhook_url":"https://example.com/webhook"}'
```

Ответ содержит `payment_id`, `status: pending`, `created_at`. Повтор с тем же ключом и телом возвращает тот же платёж; изменённое тело с тем же ключом — `409`. Для проверки статуса:

```bash
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/api/v1/payments/<payment_id>
```

Все API-запросы требуют `X-API-Key`. Поддерживаются RUB, USD, EUR; сумма должна быть положительной, максимум 18 цифр и два знака после запятой. Webhook получает JSON с `payment_id`, `status`, `processed_at` и заголовок `X-Payment-Id`. Получатель должен дедуплицировать уведомления по ID платежа: отправка webhook и подтверждение RabbitMQ не атомарны.

## Надёжность

Таблицы `payments` и `outbox` создаёт Alembic при старте API. Outbox publisher выбирает строки с `FOR UPDATE SKIP LOCKED`, публикует durable сообщение в `payments.new` и проставляет `published_at` только после подтверждения RabbitMQ. Consumer фиксирует результат в БД до webhook; повторная доставка не запускает шлюз заново. Временная ошибка повторяется до трёх раз с задержками 1 и 2 секунды. После третьей ошибки RabbitMQ кладёт событие в `payments.dlq`; очередь доступна для просмотра в панели RabbitMQ. Результат эмулятора: задержка 2–5 секунд, успех с вероятностью 90%.


## Разработка

```bash
uv sync --group dev
uv run python -m pytest -q
```

Настройки: `API_KEY` обязателен; `DATABASE_URL` и `RABBIT_URL` заданы в `compose.yaml`. Для остановки: `docker compose down`. Команда не удаляет том PostgreSQL.
