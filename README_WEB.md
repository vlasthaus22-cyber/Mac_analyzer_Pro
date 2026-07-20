# MAC Analyzer Pro Web

## Запуск

1. Используйте Python 3.10 или новее.
2. В папке проекта выполните:

   python server.py

3. Откройте http://127.0.0.1:8080

Готовые команды находятся в `scripts/`: `start_server.ps1` запускает backend
в обычном или фоновом режиме, `stop_server.ps1` останавливает фоновый процесс,
а `run_tests.ps1` запускает все проверки без установки pytest. Полная карта
каталогов приведена в `PROJECT_STRUCTURE.md`.

## Перенос на другой компьютер

Для компьютера без Python используйте автономную Windows-сборку. Создайте её на
компьютере разработчика командой:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_portable.ps1
```

Готовая папка находится в `portable/dist/MACAnalyzerBackend`. Переносить нужно
всю эту папку целиком. На другом Windows-компьютере запустите
`START_MAC_ANALYZER.cmd`: встроенный `MACAnalyzerBackend.exe` поднимет локальный
backend, дождётся успешного `/api/health` и откроет web-интерфейс. Python и pip на
целевом компьютере не требуются. `STOP_MAC_ANALYZER.cmd` корректно завершает
процесс. SQLite, история, настройки, кэш, экспорт и журналы создаются внутри
перенесённой папки в отдельных `data/`, `config/` и `logs/`; пользовательские
рабочие базы в сборку не копируются.

В исходном проекте `START_MAC_ANALYZER.cmd` также работает: при отсутствии
готового `.exe` он использует локальную `.venv`, системный Python либо создаёт
`.venv-portable` и устанавливает зависимости. Для полностью автономного переноса
предпочтительна готовая сборка с `.exe`.

## Backend API

- GET /api/health
- GET, POST, DELETE /api/mappings/vendors
- GET, POST, DELETE /api/mappings/models
- POST /api/analyze
- GET, POST, DELETE /api/snapshots
- GET /api/history?mac=001122334455
- GET /api/lookup?mac=001122334455
- GET, POST, DELETE /api/tasks
- POST /api/notifications/test
- GET /api/legacy/import/status
- POST /api/legacy/import
- GET /api/parity/status
- GET /api/parity/report
- GET /api/storage/structure

## Структура хранения

Рабочие данные отделены от исходного кода:

```text
data/
  databases/  основная SQLite-база и WAL/SHM
  legacy/     базы истории старой PyQt-версии
  backups/    резервные копии состояния
  exports/    серверные экспортные файлы
  imports/    временные импортируемые файлы
  runtime/    временные данные процессов
logs/         журналы Python и backend
config/       локальные настройки
```

При первом запуске известные файлы из корня проекта переносятся автоматически без
перезаписи уже существующих файлов. Основная база создаётся как
`data/databases/mac_analyzer_web.db`. Путь можно изменить переменными
`MAC_ANALYZER_DATA_DIR` и `MAC_ANALYZER_DATABASE_PATH`.

## Автоопределение и производительность

Backend один раз загружает правила OUI/MAC5, историю vendor/model и IP-правила
для всего анализируемого набора. Производитель определяется по самому длинному
префиксу 5/4/3 байта, затем по тексту и похожим устройствам. Модель определяется
по точному или совместимому MAC5-префиксу и истории. Пакетное сохранение истории
и ограничение обновлений прогресса устраняют отдельные SQLite-запросы для каждой
строки. Автономный JavaScript использует предварительно скомпилированные индексы.

После импорта backend возвращает временный `fileToken`: повторное обогащение
передаёт только токен, роль файла и выбранное сопоставление колонок, а не все
строки XLSX. Кэш ограничен временем, количеством файлов и строк; после
перезапуска backend frontend автоматически один раз повторяет запрос с полными
строками и получает новые токены. Список файлов и сетка сопоставления также
используют компактные payload. Частые сохранения браузера объединяются в одну
запись IndexedDB, а SQLite-autosave хранит ссылку на уже созданный снимок вместо
дублирования всех устройств и строк файлов.

Настройки серверного кэша: `MAC_ANALYZER_WORKSPACE_CACHE_TTL` (секунды),
`MAC_ANALYZER_WORKSPACE_CACHE_FILES` и `MAC_ANALYZER_WORKSPACE_CACHE_ROWS`.
Текущую статистику возвращает `GET /api/workspace/cache`. Замер JSON-payload:

```powershell
.venv\Scripts\python.exe -m tools.benchmark_workspace_payload
```

## Защита от Out of Memory

Frontend проверяет число строк, ячеек, суммарный объём текста XLSX и доступный
JS heap до создания MAC-индекса. Если безопасного запаса недостаточно, операция
останавливается управляемым сообщением `BROWSER_MEMORY_LIMIT`, не начиная
опасное выделение памяти. В автономном режиме полный результат хранится один
раз в отдельном IndexedDB snapshot-store; workspace и localStorage содержат
только ссылку, метаданные и ограниченное превью. Повторный анализ standalone
HTML освобождает предыдущий результат и временный MAC-индекс перед сохранением.

До чтения автономного файла также проверяются его сжатый размер, суммарный размер
основного и файлов обогащения, доступный JS heap, число ZIP-разделов и общий
распакованный объём XLSX. Анализ одного файла через backend передаёт XLSX бинарно,
повторно использует `fileToken` и получает только ограниченную страницу результата;
Base64- и полноразмерная JSON-копии в памяти браузера не создаются.

Для файлов, превышающих автономные лимиты, используйте переносимый backend:
он хранит полный набор и историю в SQLite, а браузеру возвращает только страницу
результатов размером 25–1000 строк.

External OUI lookup is disabled by default. To enable it, set
MAC_ANALYZER_ENABLE_EXTERNAL_LOOKUP=true before starting the server.

SMTP credentials are accepted only for the test request and are never written
to the SQLite database.

## Проверка parity

Запустите полный набор проверок без зависимости от pytest:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_tests.ps1
```

Отдельная smoke-проверка REST API и UI-контролов:

```powershell
.venv\Scripts\python.exe -m tests.test_web_api_ui_smoke
```

Обновить машинный отчёт переноса:

```powershell
.venv\Scripts\python.exe -m tools.generate_parity_status
```
