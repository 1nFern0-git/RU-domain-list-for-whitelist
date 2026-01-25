# Белые списки доменов и IP-адресов в зоне .ru

Проект собирает домены и IP-адреса в зоне .ru для создания белых списков мобильных операторов России.

## Цель проекта

Сбор и проверка доменов и IP-адресов, применяемых операторами мобильной связи при частичном ограничении доступа в интернет («Белые списки»). Собранные данные можно использовать для построения правил маршрутизации для ядра Xray.

## Автоматическая сборка .dat файлов

Этот репозиторий автоматически собирает объединенные `geosite.dat` и `geoip.dat` файлы, комбинируя категории из [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat) и whitelist категорию из текущего репозитория.

### Периодичность обновлений

- Автоматическая сборка происходит **ежедневно в 03:00 UTC**
- Релиз создается автоматически с версией в формате `YYYYMMDD` (например, `20260125`)
- Можно также запустить сборку вручную через GitHub Actions

### Скачивание готовых файлов

Скачать последнюю версию файлов можно из релизов:

- **geosite.dat**: [Скачать последнюю версию](https://github.com/1nFern0-git/RU-domain-list-for-whitelist/releases/latest/download/geosite.dat)
- **geoip.dat**: [Скачать последнюю версию](https://github.com/1nFern0-git/RU-domain-list-for-whitelist/releases/latest/download/geoip.dat)

Все релизы доступны на странице [Releases](https://github.com/1nFern0-git/RU-domain-list-for-whitelist/releases).

### Включенные категории

**В `geosite.dat`:**

- **category-ru**: Российские домены из runetfreedom
- **ru-blocked**: Заблокированные в России домены
- **ru-available-only-inside**: Домены, доступные только внутри России
- **category-ads-all**: Все рекламные домены (AdguardFilterDNS, PeterLoweFilter и другие)
- **whitelist**: Проверенные whitelist домены из текущего репозитория (domains/ru/)
- **whitelist-ads**: Рекламные домены из текущего репозитория (domains/ads/)

**В `geoip.dat`:**

- **ru**: Российские IP-диапазоны
- **ru-blocked**: Заблокированные IP-диапазоны
- **private**: Приватные IP-диапазоны
- **whitelist**: Проверенные whitelist IP-адреса из текущего репозитория

## Использование с v2ray/Xray

Скачайте файлы и поместите их в директорию конфигурации v2ray/Xray (обычно `/usr/local/share/xray/` или `/usr/local/share/v2ray/`).

### Пример конфигурации

```json
{
  "routing": {
    "domainStrategy": "IPIfNonMatch",
    "rules": [
      {
        "type": "field",
        "domain": [
          "geosite:whitelist",
          "geosite:category-ru"
        ],
        "outboundTag": "direct"
      },
      {
        "type": "field",
        "ip": [
          "geoip:whitelist",
          "geoip:ru"
        ],
        "outboundTag": "direct"
      },
      {
        "type": "field",
        "domain": ["geosite:category-ads-all"],
        "outboundTag": "block"
      }
    ]
  }
}
```

Полный пример конфигурации можно посмотреть в [JSON_example](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/JSON_example).

## Настройка категорий

Если вы хотите изменить список включаемых категорий, отредактируйте файл [`scripts/config.yml`](scripts/config.yml):

```yaml
# Категории для извлечения из runetfreedom/russia-v2ray-rules-dat geosite.dat
geosite_categories:
  - category-ru
  - ru-blocked
  - ru-available-only-inside
  - category-ads-all

# Категории для извлечения из runetfreedom/russia-v2ray-rules-dat geoip.dat
geoip_categories:
  - ru
  - ru-blocked
  - private
```

После изменения конфигурации, следующая автоматическая сборка будет использовать новые настройки.

## Самостоятельная сборка

Если вы хотите собрать файлы локально:

### Требования

- Python 3.12+
- pip

### Шаги сборки

1. Клонируйте репозиторий:
```bash
git clone https://github.com/1nFern0-git/RU-domain-list-for-whitelist.git
cd RU-domain-list-for-whitelist
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Скомпилируйте protobuf определения:
```bash
cd scripts
python -m grpc_tools.protoc -I. --python_out=. common.proto
cd ..
```

4. Запустите парсинг исходных файлов:
```bash
python scripts/parse_dat.py \
  --source-repo runetfreedom/russia-v2ray-rules-dat \
  --geosite-categories category-ru ru-blocked ru-available-only-inside category-ads-all \
  --geoip-categories ru ru-blocked private \
  --output-dir output
```

5. Соберите финальные файлы:
```bash
python scripts/build_dat.py \
  --extracted-geosite output/extracted_geosite.dat \
  --extracted-geoip output/extracted_geoip.dat \
  --whitelist-domains domains/ru/category-ru \
  --whitelist-ads domains/ads \
  --whitelist-ips IPs \
  --output-dir output
```

6. Готовые файлы будут в директории `output/`:
   - `output/geosite.dat`
   - `output/geoip.dat`

## Структура проекта

```
.github/
  workflows/
    build-dat-files.yml    # GitHub Actions workflow для автоматической сборки
scripts/
  parse_dat.py             # Скрипт парсинга .dat файлов
  build_dat.py             # Скрипт генерации .dat файлов
  common.proto             # Protocol Buffers определения
  config.yml               # Конфигурация категорий
domains/                   # Списки доменов по категориям
IPs/                       # Списки подсетей по категориям
IPсhecked/                 # Проверенные IP-адреса
requirements.txt           # Python зависимости
```

## Актуальные (проверенные) данные

Проверенные на работоспособность у всех операторов категории (домены) смотри в [`/domains/ru/category-ru`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/domains/ru/category-ru)

Проверенные IP-адреса в БС смотри в [`/IPсhecked`](https://github.com/kirilllavrov/RU-domain-list-for-whitelist/blob/main/IPсhecked)

## Связанные проекты

- **Исходные категории**: [runetfreedom/russia-v2ray-rules-dat](https://github.com/runetfreedom/russia-v2ray-rules-dat)
- **v2ray domain list**: [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)
- **v2ray geoip**: [v2fly/geoip](https://github.com/v2fly/geoip)

## Техническая информация

### Формат .dat файлов

Файлы используют Protocol Buffers формат v2ray/Xray. Структура определена в [`scripts/common.proto`](scripts/common.proto).

### Обработка категорий

- Скрипты поддерживают case-insensitive поиск категорий
- Все кастомные категории из runetfreedom корректно обрабатываются
- Whitelist категория добавляется автоматически при каждой сборке

## Лицензия

См. LICENSE файл в репозитории.