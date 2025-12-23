# Списки доменов и ip адресов в зоне Ru

Проект собирает домены и ip адреса в зоне RU для создания белых списков мобильных операторов России

## Цель этого проекта

Сбор проверка доменов и ip адресов, применяемых операторами мобильной связи при частичном ограничении доступа в интернет, "Белые списки". Собранные данные можно использовать для построения правил маршрутизации для Xray ядра.

## Структура проекта

Для удобства работы с данными "Белые списки" разделены на списки IP адресов - /IPs, и списки доменов - /domains

## Самостоятельная сборка файлов geosite.dat geoip.dat для маршрутизации

Инструмент и мануал по сборке geosite.dat - [https://github.com/v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)

Инструмент и мануал по сборке geoip.dat - [hhttps://github.com/v2fly/geoip](https://github.com/v2fly/geoip)

## Ссылки для скачивания

Готовый работающий БС для Xray

- **geosite.dat**：[https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/dlc.dat)

- **geoip.dat**：[https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat)

## Категории в geosite.dat geoip.dat

Для удобства построения маршрутизации нужно применять следующие категории:

**geosite.dat** содержит категории "category-ru", "category-ads-all" и "private":

- **category-ru**: содержит известные домены, включенные в "Белые списки"

- **category-ads-all**: содержит рекламмные домены

- **private**: содержит приватные домены

**geoip.dat** содержит категорию "whitelist" - все известные IP адреса, включенные в "Белые списки".