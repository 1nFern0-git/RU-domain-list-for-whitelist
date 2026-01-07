#!/usr/bin/env python3
import sys
import subprocess
import socket
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Set, Tuple, Dict, List

# === НАСТРОЙКИ ===
SRC_DIR = Path("./domains/ru")
# RESULTS_DIR = Path("./results") # Убрана директория результатов
# RESULTS_DIR.mkdir(exist_ok=True) # Убрана
PING_COUNT = 4
PING_TIMEOUT_SEC = 6
MAX_WORKERS = 5
TCP_TIMEOUT = 6  # секунд на попытку подключиться к порту
DEFAULT_PORTS = [443, 80, 8080]  # Порты, которые проверяем по TCP

# Имена файлов, которые нужно исключить из проверки
EXCLUDE_FILES = {"category-ru", "private", "gov"}
# =================

def load_domains_from_file(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Читает файл и возвращает два списка:
    1. Строки с доменами (до обработки, без #)
    2. Все строки файла (для последующей записи)
    """
    original_lines = []
    domains_to_check = []
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            all_lines = file.readlines()

        for line in all_lines:
            original_lines.append(line)
            # Убираем комментарии *после* домена, разделяя по #
            line_part = line.split('#')[0].strip()
            if line_part:
                # Извлекаем домен: убираем http://, https://, порты, пути
                temp_domain = line_part.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
                if temp_domain and '.' in temp_domain:
                    try:
                        # Преобразуем IDN в ASCII (Punycode) для ping и TCP
                        ascii_domain = temp_domain.encode('idna').decode('ascii')
                        domains_to_check.append(ascii_domain)
                    except (UnicodeError, UnicodeDecodeError):
                        print(f"   ⚠️  Пропущена строка '{line.strip()}': '{temp_domain}' (ошибка преобразования IDN)")
    except UnicodeDecodeError:
        print(f"   ⚠️  Ошибка кодировки в файле {filepath.name}, пробую cp1251...")
        try:
            with open(filepath, "r", encoding="cp1251") as file:
                all_lines = file.readlines()
            for line in all_lines:
                original_lines.append(line)
                line_part = line.split('#')[0].strip()
                if line_part:
                    temp_domain = line_part.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
                    if temp_domain and '.' in temp_domain:
                        try:
                            ascii_domain = temp_domain.encode('idna').decode('ascii')
                            domains_to_check.append(ascii_domain)
                        except (UnicodeError, UnicodeDecodeError):
                            print(f"   ⚠️  Пропущена строка '{line.strip()}': '{temp_domain}' (ошибка преобразования IDN)")
        except Exception as e:
            print(f"   ❌ Не удалось прочитать файл {filepath.name} ни с utf-8, ни с cp1251: {e}")
            return [], [] # Возвращаем пустые списки в случае ошибки
    except Exception as e:
        print(f"   ❌ Ошибка чтения {filepath.name}: {e}")
        return [], []

    return domains_to_check, original_lines

def load_domains() -> Tuple[Dict[str, Path], List[str]]:
    """
    Загружает домены из всех файлов в SRC_DIR, исключая указанные в EXCLUDE_FILES.
    Возвращает словарь: {ascii_domain: Path_to_file} и список всех уникальных доменов для проверки.
    """
    domain_to_file_map = {}
    unique_domains = set()

    if not SRC_DIR.exists():
        print(f"❌ Папка '{SRC_DIR}' не найдена.")
        sys.exit(1)

    # Ищем файлы *без* расширения (суффикса), исключая указанные
    domain_files = [
        f for f in SRC_DIR.iterdir()
        if f.is_file() and f.suffix == '' and f.name not in EXCLUDE_FILES
    ]

    if not domain_files:
        print(f"📂 В '{SRC_DIR}' нет файлов без расширения, кроме исключённых: {list(EXCLUDE_FILES)}.")
        sys.exit(0)

    print(f"📂 Найдено {len(domain_files)} файл(ов) для проверки: {[f.name for f in domain_files]}")
    print(f"   (исключены: {list(EXCLUDE_FILES)})")

    for f in domain_files:
        print(f"   Обработка файла: {f.name}")
        domains_in_file, _ = load_domains_from_file(f)
        for domain in domains_in_file:
            # Если домен встречается в нескольких файлах, сопоставляем с первым
            if domain not in domain_to_file_map:
                domain_to_file_map[domain] = f
            unique_domains.add(domain)

    if not unique_domains:
        print("笼罩 Нет валидных доменов для проверки.")
        sys.exit(0)

    print(f"✅ Всего уникальных доменов: {len(unique_domains)}\n")
    return domain_to_file_map, list(unique_domains)

def check_tcp_port(domain: str, port: int) -> bool:
    """Проверяет, открыт ли указанный TCP-порт на домене."""
    try:
        with socket.create_connection((domain, port), timeout=TCP_TIMEOUT):
            return True
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return False

def check_domain(domain: str) -> Tuple[str, bool]:
    """Проверяет доступность домена: сначала TCP, затем ping."""
    # Сначала TCP-соединение
    for port in DEFAULT_PORTS:
        if check_tcp_port(domain, port):
            return domain, True

    # Если TCP неудачно, пробуем ping
    try:
        cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT_SEC), domain]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=PING_TIMEOUT_SEC * PING_COUNT + 2)
        if result.returncode == 0:
            return domain, True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass  # ping не удался

    return domain, False

def comment_out_domain_in_file(filepath: Path, domain_to_comment: str):
    """
    Комментирует *первое* вхождение указанного домена (в его ASCII/IDN форме) в файле.
    """
    # Читаем файл заново, чтобы получить список строк
    _, original_lines = load_domains_from_file(filepath)
    if not original_lines:
        print(f"⚠️ Не удалось прочитать {filepath} для комментирования.")
        return

    domain_found_and_commented = False
    commented_lines = []
    for line in original_lines:
        if domain_found_and_commented:
            commented_lines.append(line)
            continue

        # Проверяем, содержит ли строка домен (до #)
        line_part = line.split('#')[0].strip()
        if line_part:
            temp_domain = line_part.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
            if temp_domain and '.' in temp_domain:
                try:
                    ascii_line_domain = temp_domain.encode('idna').decode('ascii')
                    if ascii_line_domain == domain_to_comment and not line.strip().startswith('#'):
                        # Комментируем строку
                        commented_lines.append("# " + line.lstrip()) # Добавляем "# " в начало
                        domain_found_and_commented = True
                        continue
                except (UnicodeError, UnicodeDecodeError):
                    pass # Пропускаем, если ошибка IDN
        commented_lines.append(line)

    if domain_found_and_commented:
        # Перезаписываем файл с комментированными строками
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                file.writelines(commented_lines)
            # print(f"   ℹ️ Закомментирован домен '{domain_to_comment}' в файле {filepath.name}")
        except Exception as e:
            print(f"   ❌ Ошибка записи в {filepath.name}: {e}")
    else:
        print(f"   ⚠️ Не удалось найти или закомментировать домен '{domain_to_comment}' в файле {filepath.name} (неожиданное поведение).")


def main():
    domain_to_file_map, all_domains = load_domains()
    total = len(all_domains)

    # Проверяем наличие ping
    ping_available = subprocess.run(["which", "ping"], stdout=subprocess.DEVNULL).returncode == 0
    if not ping_available:
        print("⚠️  'ping' не найден. Проверки будут только по TCP-портам.")
    else:
        print(f"⚡ Проверка {total} доменов (TCP {DEFAULT_PORTS}, затем ping, до {MAX_WORKERS} параллельно)...\n")
    if not ping_available:
        print(f"⚡ Проверка {total} доменов (только TCP {DEFAULT_PORTS}, до {MAX_WORKERS} параллельно)...\n")

    available_count = 0
    unavailable_count = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(check_domain, domain) for domain in all_domains]
        for i, future in enumerate(as_completed(futures), 1):
            domain, is_alive = future.result()
            status = "✅" if is_alive else "❌"
            try:
                original_domain = domain.encode('ascii').decode('idna')
            except (UnicodeError, UnicodeDecodeError):
                original_domain = domain
            print(f"[{i:>{len(str(total))}}/{total}] {status} {original_domain}")
            if is_alive:
                available_count += 1
            else:
                unavailable_count += 1
                # Комментируем недоступный домен в его исходном файле
                source_file = domain_to_file_map.get(domain)
                if source_file:
                    comment_out_domain_in_file(source_file, domain)
                else:
                    print(f"⚠️ Не найден файл для домена {domain} (ошибка в карте).")


    print("\n" + "═" * 50)
    print(f"✅ Доступны (TCP/ping):   {available_count}")
    print(f"❌ Недоступны (TCP/ping): {unavailable_count} (закомментированы в исходных файлах)")
    # print(f"\n📁 Результаты сохранены:") # Убран вывод о файлах
    # print(f"   → {RESULTS_DIR}/tcp_ping_available.txt") # Убран
    # print(f"   → {RESULTS_DIR}/tcp_ping_unavailable.txt") # Убран

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Прервано пользователем.")
        sys.exit(1)
