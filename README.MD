# EasyQiwi 🥝

Модуль `easyqiwi` - асинхронный Python модуль для работы с QIWI API. Он позволяет легко интегрировать функционал QIWI кошелька в ваши Python приложения. С помощью `easyqiwi` вы можете получать профиль пользователя, баланс счетов, историю платежей, генерировать счета и многое другое!

## Основные возможности

- Получение профиля пользователя 👤
- Управление счетами 💳
- Просмотр истории платежей 🔍
- Создание счетов для оплаты (инвойсов) 🧾
- Асинхронная работа ⚙️
- Поддержка прокси 🌐
- Есть обработка каптчи 🔒

## Быстрый старт

Пример асинхронного использования `easyqiwi` для аутентификации в QIWI и создания счета для оплаты:

```python
import asyncio
from easyqiwi import EasyQiwiAuthCore, EasyQiwiAPI, setup_proxy
from easyqiwi import AuthException

async def main():
    phone = '+79228133736'
    password = 'example'
    proxy_tuple = await setup_proxy('socks5', '162.210.192.136', '25881')

    qiwi = EasyQiwiAuthCore(phone, password, proxy_tuple)

    try:
        await qiwi.auth()
    except AuthException as e:
        print(e)
        exit()

    qiwi_api = EasyQiwiAPI(qiwi)
    p2p_resp = await qiwi_api.generate_p2p_public()
    p2p_key = p2p_resp['publicKey']
    widget_code = p2p_resp['widgetAliasCode']
    invoice_resp = await qiwi_api.create_invoice(p2p_key, widget_code, 100)
    invoice_uid = invoice_resp['invoice_uid']

    print(f'https://oplata.qiwi.com/form?invoiceUid={invoice_uid}')

    await qiwi.close()

if __name__ == '__main__':
    asyncio.run(main())
```

В этом примере мы создаем асинхронное соединение с QIWI, аутентифицируемся и создаем счет на оплату в 100 рублей.

## Установка

Установить модуль `easyqiwi` можно через `pip`:

```bash
pip install easyqiwi
```

## Небольшая документация

### Аутентификация

Чтобы начать работу с QIWI API, необходимо произвести аутентификацию, используя номер телефона и пароль от QIWI кошелька:

```python
qiwi = EasyQiwiAuthCore(phone, password)
await qiwi.auth()
```

### Обработка каптчи

Можно обработать каптчу, если она выскакивает:

```python
from easyqiwi import RecaptchaException

try:
	qiwi = EasyQiwiAuthCore(phone, password)
	await qiwi.auth()
except RecaptchaException as e:
	# и тут можно решать каптчу и затем вызвать
	await qiwi.auth(recaptcha='обработанная каптча')
```

### Получение профиля

Получение данных профиля пользователя:

```python
qiwi_api = EasyQiwiAPI(qiwi)
profile = await qiwi_api.get_current_profile()
print(profile)
```

### История платежей

Получение истории платежей:

```python
payments = await qiwi_api.get_payments(person_id, rows=10)
print(payments)
```

### Создание инвойса

Генерация и отправка инвойса для оплаты:

```python
invoice_resp = await qiwi_api.create_invoice(p2p_key, widget_code, 500, comment='За услуги')
invoice_uid = invoice_resp['invoice_uid']
print(f'Ссылка для оплаты: https://oplata.qiwi.com/form?invoiceUid={invoice_uid}')
```

### Закрытие сессии

Не забудьте закрыть сессию при завершении работы:

```python
await qiwi.close()
```

## Прокси

Если вам необходимо использовать прокси, вы можете настроить его следующим образом:

```python
proxy_tuple = await setup_proxy('socks5', 'proxy_ip', 'proxy_port', 'username', 'password')
```