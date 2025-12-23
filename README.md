# Белые списки доменов и IP-адресов в зоне .ru

Проект собирает домены и IP-адреса в зоне .ru для создания белых списков мобильных операторов России.

## Цель проекта

Сбор и проверка доменов и IP-адресов, применяемых операторами мобильной связи при частичном ограничении доступа в интернет («Белые списки»). Собранные данные можно использовать для построения правил маршрутизации для ядра Xray.

## Структура проекта

Для удобства работы с данными «Белые списки» разделены на:

- Списки IP-адресов — `/IPs`
- Списки доменов — `/domains`

## Самостоятельная сборка файлов `geosite.dat` и `geoip.dat` для маршрутизации

Инструменты и инструкции по сборке:

- **geosite.dat**: [https://github.com/v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- **geoip.dat**: [https://github.com/v2fly/geoip](https://github.com/v2fly/geoip)

## Ссылки для скачивания готовых файлов

Готовые рабочие файлы для Xray:

- **geosite.dat**: [https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat)
- **geoip.dat**: [https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat)

## Категории в `geosite.dat` и `geoip.dat`

Для удобства настройки маршрутизации используйте следующие категории:

**В `geosite.dat`:**

- **category-ru**: известные домены, включённые в «Белые списки»
- **category-ads-all**: рекламные домены
- **private**: приватные домены

**В `geoip.dat`:**

- **whitelist**: все известные IP-адреса, включённые в «Белые списки» операторов.