#!/usr/bin/env python3
import sys
import subprocess
import socket
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Tuple, Dict, List

# === НАСТРОЙКИ ===
SRC_DIR = Path("./domains/ru")
PING_COUNT = 4
PING_TIMEOUT_SEC = 5
MAX_WORKERS = 10
TCP_TIMEOUT = 6  # секунд на попытку подключиться к порту
DEFAULT_PORTS = [443, 80, 8080, 8443]  # Порты, которые проверяем по TCP
EXCLUDE_FILES = {"category-ru", "private", "category-whitelist-ru"}
# =================


def load_domains_from_file(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Читает файл и возвращает два списка:
    1. Список ASCII-доменов для проверки (включая из закомментированных строк)
    2. Все исходные строки файла (для последующей записи)
    """
    original_lines = []
    domains_to_check = []

    def extract_domain_from_line(line: str) -> str | None:
        """Извлекает домен из строки, даже если она закомментирована."""
        stripped = line.strip()
        # Убираем начальный '#', если есть
        if stripped.startswith('#'):
            content = stripped[1:].strip()
        else:
            content = stripped

        # Убираем inline-комментарии
        content = content.split('#')[0].strip()

        if not content:
            return None

        # Извлекаем чистый домен
        temp_domain = content.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
        if temp_domain and '.' in temp_domain:
            try:
                return temp_domain.encode('idna').decode('ascii')
            except (UnicodeError, UnicodeDecodeError):
                print(f"   ⚠️  Пропущена строка '{line.strip()}': '{temp_domain}' (ошибка преобразования IDN)")
                return None
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            all_lines = file.readlines()
        for line in all_lines:
            original_lines.append(line)
            domain = extract_domain_from_line(line)
            if domain:
                domains_to_check.append(domain)
    except UnicodeDecodeError:
        print(f"   ⚠️  Ошибка кодировки в файле {filepath.name}, пробую cp1251...")
        try:
            with open(filepath, "r", encoding="cp1251") as file:
                all_lines = file.readlines()
            original_lines.clear()
            domains_to_check.clear()
            for line in all_lines:
                original_lines.append(line)
                domain = extract_domain_from_line(line)
                if domain:
                    domains_to_check.append(domain)
        except Exception as e:
            print(f"   ❌ Не удалось прочитать файл {filepath.name} ни с utf-8, ни с cp1251: {e}")
            return [], []
    except Exception as e:
        print(f"   ❌ Ошибка чтения {filepath.name}: {e}")
        return [], []

    return domains_to_check, original_lines


def load_domains() -> Tuple[Dict[str, Path], List[str]]:
    domain_to_file_map = {}
    unique_domains = set()

    if not SRC_DIR.exists():
        print(f"❌ Папка '{SRC_DIR}' не найдена.")
        sys.exit(1)

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
            if domain not in domain_to_file_map:
                domain_to_file_map[domain] = f
            unique_domains.add(domain)

    if not unique_domains:
        print("笼罩 Нет валидных доменов для проверки.")
        sys.exit(0)

    print(f"✅ Всего уникальных доменов: {len(unique_domains)}")
    return domain_to_file_map, list(unique_domains)


def check_tcp_port(domain: str, port: int) -> bool:
    try:
        with socket.create_connection((domain, port), timeout=TCP_TIMEOUT):
            return True
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return False


def check_domain(domain: str) -> Tuple[str, bool]:
    for port in DEFAULT_PORTS:
        if check_tcp_port(domain, port):
            return domain, True

    try:
        cmd = ["ping", "-c", str(PING_COUNT), "-W", str(PING_TIMEOUT_SEC), domain]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=PING_TIMEOUT_SEC * PING_COUNT + 2)
        if result.returncode == 0:
            return domain, True
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass

    return domain, False


def comment_out_domain_in_file(filepath: Path, domain_to_comment: str):
    """Комментирует домен, если он ещё не закомментирован."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            original_lines = file.readlines()
    except Exception as e:
        print(f"⚠️ Не удалось прочитать {filepath} для комментирования: {e}")
        return

    updated_lines = []
    found = False

    for line in original_lines:
        if found:
            updated_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            updated_lines.append(line)
            continue

        # Извлекаем домен из строки (игнорируя комментарии)
        content = stripped
        if content.startswith('#'):
            real_content = content[1:].strip()
        else:
            real_content = content

        real_content = real_content.split('#')[0].strip()
        if not real_content:
            updated_lines.append(line)
            continue

        temp_domain = real_content.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
        if temp_domain and '.' in temp_domain:
            try:
                ascii_line_domain = temp_domain.encode('idna').decode('ascii')
                if ascii_line_domain == domain_to_comment:
                    if not stripped.startswith('#'):
                        # Комментируем
                        leading = line[:len(line) - len(line.lstrip())]
                        updated_lines.append(leading + "# " + line.lstrip())
                    else:
                        updated_lines.append(line)  # уже закомментировано
                    found = True
                    continue
            except (UnicodeError, UnicodeDecodeError):
                pass

        updated_lines.append(line)

    if found:
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                file.writelines(updated_lines)
        except Exception as e:
            print(f"   ❌ Ошибка записи в {filepath.name}: {e}")


def uncomment_domain_in_file(filepath: Path, domain_to_uncomment: str):
    """Раскомментирует домен, если он закомментирован."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            original_lines = file.readlines()
    except Exception as e:
        print(f"⚠️ Не удалось прочитать {filepath} для раскомментирования: {e}")
        return

    updated_lines = []
    found = False

    for line in original_lines:
        if found:
            updated_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped or not stripped.startswith('#'):
            updated_lines.append(line)
            continue

        content_after_hash = stripped[1:].strip()
        if not content_after_hash:
            updated_lines.append(line)
            continue

        real_content = content_after_hash.split('#')[0].strip()
        if not real_content:
            updated_lines.append(line)
            continue

        temp_domain = real_content.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
        if temp_domain and '.' in temp_domain:
            try:
                ascii_line_domain = temp_domain.encode('idna').decode('ascii')
                if ascii_line_domain == domain_to_uncomment:
                    # Раскомментируем
                    leading = line[:len(line) - len(line.lstrip())]
                    rest = stripped[1:]
                    if rest.startswith(' '):
                        rest = rest[1:]
                    updated_lines.append(leading + rest + '\n')
                    found = True
                    continue
            except (UnicodeError, UnicodeDecodeError):
                pass

        updated_lines.append(line)

    if found:
        try:
            with open(filepath, "w", encoding="utf-8") as file:
                file.writelines(updated_lines)
        except Exception as e:
            print(f"   ❌ Ошибка записи при раскомментировании {filepath.name}: {e}")


def is_domain_commented_in_file(filepath: Path, domain: str) -> bool:
    """Проверяет, закомментирован ли домен в файле."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except:
        return False

    for line in lines:
        stripped = line.strip()
        if not stripped.startswith('#'):
            continue
        content = stripped[1:].split('#')[0].strip()
        if not content:
            continue
        temp_domain = content.split("://")[-1].split("/")[0].split(":")[0].strip().lower()
        if temp_domain and '.' in temp_domain:
            try:
                ascii_cand = temp_domain.encode('idna').decode('ascii')
                if ascii_cand == domain:
                    return True
            except:
                pass
    return False


def main():
    domain_to_file_map, all_domains = load_domains()
    total = len(all_domains)

    ping_available = subprocess.run(["which", "ping"], stdout=subprocess.DEVNULL).returncode == 0
    if not ping_available:
        print("⚠️  'ping' не найден. Проверки будут только по TCP-портам.")
        print(f"⚡ Проверка {total} доменов (только TCP {DEFAULT_PORTS}, до {MAX_WORKERS} параллельно)...\n")
    else:
        print(f"⚡ Проверка {total} доменов (TCP {DEFAULT_PORTS}, затем ping, до {MAX_WORKERS} параллельно)...\n")

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

            source_file = domain_to_file_map.get(domain)
            if not source_file:
                continue

            if is_alive:
                available_count += 1
                if is_domain_commented_in_file(source_file, domain):
                    uncomment_domain_in_file(source_file, domain)
            else:
                unavailable_count += 1
                comment_out_domain_in_file(source_file, domain)

    print("\n" + "═" * 50)
    print(f"✅ Доступны (TCP/ping):   {available_count}")
    print(f"❌ Недоступны (TCP/ping): {unavailable_count} (обновлены в исходных файлах)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Прервано пользователем.")
        sys.exit(1)
