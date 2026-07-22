# Структура MAC Analyzer Pro

```text
Mac_analyzer_Pro/
  .agents/                 контекст сопровождения, не используется программой
  .git/                    локальная история и настройки Git
  scripts/                 единые команды запуска, остановки и тестирования
  tests/                   регрессионные, API и parity-проверки
    test_repeated_enrichment_memory.py обязательный четырёхкратный стресс-тест двухфайлового обогащения
    frontend_repeated_persistence_memory.test.js четыре сохранения 100 000 локальных устройств без второй копии результата
    frontend_snapshot_chunking_memory.test.js четыре порционных снимка по 120 000 устройств
    frontend_real_xlsx_repeated_enrichment.test.js три полных чтения реального XLSX на 100 000 строк с контролем удержанной heap-памяти
    frontend_xlsx_shared_strings_streaming.test.js три потоковых чтения 120 000 shared strings без удержания XML
    workspace_file_lifecycle.test.js замена использованных файлов обогащения без удаления снимков и истории
    local_folder_store.test.js создание локальной структуры, базы, манифеста, архива импорта и журнала
    standalone_inline_syntax.test.js компиляция всего встроенного JavaScript переносимого HTML
  tools/                   parity, benchmark и legacy-утилиты
  frontend/                браузерные модули импорта, контроля памяти и безопасного хранения состояния
    memory-guard.js        ранние лимиты файла/ZIP/heap, суммы файлов обогащения, локального экспорта, paging и cooperative yield
    file-readers.js        потоковый XLSX/CSV/JSON-импорт с проверкой ZIP-каталога до распаковки XML
    browser-snapshot-store.js порционное IndexedDB-хранилище локальных снимков без полной копии при записи
    portable-database.js  потоковая файловая база MADB для переноса данных между браузерами и ПК
    local-folder-store.js локальная структура database/imports/exports/settings/logs/backups, сохранённая ссылка браузера и дедупликация повторных импортов
    workspace-file-lifecycle.js жизненный цикл файлов: использованные входы заменяются в следующем запуске, история остаётся в снимках
    state-persistence.js   компактное сохранение workspace; полный локальный результат хранится один раз в snapshot-store, аварийная inline-копия ограничена 20 000 строк
    guide.js               руководство, переключение разделов и отображение текущего режима
  backend/
    services/
      detection/           OUI, vendor/model, индексы и колонки
        reference_data_service.py импорт IEEE/corporate OUI TXT/CSV и синхронизация SQLite
      workspace/           XLSX/CSV, enrichment, single-file и кэш
      analytics/           графики, dashboard, отчёты, топология и кластеры
      integrations/        внешние API, уведомления и планировщик
      comparison/          сравнение двух и нескольких выгрузок
      exporting/           CSV/TXT/HTML/JSON/YAML/XLSX/PDF экспорт
      system/              пути хранения, legacy-миграция и parity-аудит
        diagnostics_service.py read-only самодиагностика SQLite, API, структуры и OOM-защиты
  config/                  локальные настройки
  data/
    databases/             рабочая SQLite-база и WAL/SHM
    legacy/                базы исходной PyQt-программы
    backups/               резервные копии
    imports/               входные файлы и ограниченный workspace-cache для больших таблиц
      workspace-cache/     workspace_cache.db со строками импортов; backend читает их пакетами без RAM-кэша таблиц
    reference/             переносимые OUI TXT/CSV для автоопределения производителей
    exports/               серверные результаты экспорта
    runtime/               PID и временное состояние процессов
      tests/               временные изолированные базы тестов; автоматически очищаются
  logs/                    журналы backend и исходной программы
  portable/                готовые пользовательские сборки (создаются командами сборки, не хранятся в Git)
    html/MAC-Analyzer-Pro.html один автономный файл без EXE, CMD, Python и backend
    complete/*.zip        полный проект, автономный HTML и локальные данные без EXE/DLL/CMD
    dist/MACAnalyzerBackend/ единый пакет: исходный server.py, Python-first лаунчер и резервный asInvoker backend
  START_MAC_ANALYZER.cmd    запуск переносимого backend и открытие web-интерфейса
  STOP_MAC_ANALYZER.cmd     остановка переносимого backend
  index.html               HTML-интерфейс и автономный browser fallback
  mac_analyzer_standalone.html устаревший parity-артефакт; в пользовательскую сборку не включается
  app.js                   основная логика web frontend
  styles.css               стили web frontend
  server.py                HTTP API, SQLite и раздача frontend
  *_service.py             совместимые импорты и ещё не сгруппированные сервисы
  MAC_ANALYZER финальная.py исходный PyQt-файл для проверки parity
```

Корневые `*_service.py`, для которых уже создан пакет, содержат только
совместимый импорт старого имени. Рабочая реализация находится в `backend/services`.

Служебные каталоги отделены от рабочих данных. `.agents` не содержит код
приложения. `.git` создаётся командой `git init` и не должна редактироваться
вручную. Тесты изолированы в `tests/`, используют временный
`data/runtime/tests/<run-id>` вместо рабочей SQLite-базы и запускаются как Python-модули,
а служебные команды в `tools/` используют единый `_bootstrap.py` для импорта backend.

## Команды

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_server.ps1
powershell -ExecutionPolicy Bypass -File scripts/start_server.ps1 -Background
powershell -ExecutionPolicy Bypass -File scripts/stop_server.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/build_portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/build_html_portable.ps1
powershell -ExecutionPolicy Bypass -File scripts/build_complete_release.ps1
```

## SQLite-обогащение без накопления памяти браузера

Backend хранит импортированные строки в `data/imports/workspace-cache/workspace_cache.db`.
Frontend сохраняет только токен файла, заголовки и не более 100 строк предпросмотра.
`/api/enrichment/run` читает строки из SQLite пакетами; полный результат и история
записываются в `data/databases/mac_analyzer_web.db`, а браузер получает одну страницу.
После успешного запуска использованный файл обогащения удаляется из рабочего SQLite-кэша
при выборе следующего файла. Снимки, история MAC и журнал изменений при этом сохраняются.

Автономный HTML не использует backend: полные результаты находятся в IndexedDB-базе
`mac-analyzer-browser-storage-v1`, в хранилищах `snapshots` и `snapshotChunks`. Снимки
записываются и читаются блоками по 1 000 строк, а `state.devices` содержит только открытую
страницу. Это локальная дисковая база профиля браузера; изолированный HTML не может напрямую
открывать SQLite-файл без разрешения браузера или серверного процесса.
