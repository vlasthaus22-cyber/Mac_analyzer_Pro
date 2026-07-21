# Структура MAC Analyzer Pro

```text
Mac_analyzer_Pro/
  .agents/                 контекст сопровождения, не используется программой
  .git/                    локальная история и настройки Git
  scripts/                 единые команды запуска, остановки и тестирования
  tests/                   регрессионные, API и parity-проверки
    test_repeated_enrichment_memory.py обязательный четырёхкратный стресс-тест двухфайлового обогащения
    frontend_repeated_persistence_memory.test.js четыре сохранения 100 000 локальных устройств без второй копии результата
    standalone_inline_syntax.test.js компиляция всего встроенного JavaScript переносимого HTML
  tools/                   parity, benchmark и legacy-утилиты
  frontend/                браузерные модули импорта, контроля памяти и безопасного хранения состояния
    memory-guard.js        ранние лимиты файла/ZIP/heap, суммы файлов обогащения, локального экспорта, paging и cooperative yield
    file-readers.js        потоковый XLSX/CSV/JSON-импорт с проверкой ZIP-каталога до распаковки XML
    browser-snapshot-store.js отдельное IndexedDB-хранилище полных локальных снимков
    state-persistence.js   компактное сохранение workspace; полный локальный результат хранится один раз в snapshot-store
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
      workspace-cache/     полные таблицы по токену с TTL для восстановления backend
    reference/             переносимые OUI TXT/CSV для автоопределения производителей
    exports/               серверные результаты экспорта
    runtime/               PID и временное состояние процессов
      tests/               временные изолированные базы тестов; автоматически очищаются
  logs/                    журналы backend и исходной программы
  portable/                результат автономной Windows-сборки (создаётся командой сборки, не хранится в Git)
  START_MAC_ANALYZER.cmd    запуск переносимого backend и открытие web-интерфейса
  STOP_MAC_ANALYZER.cmd     остановка переносимого backend
  index.html               HTML-интерфейс и автономный browser fallback
  mac_analyzer_standalone.html переносимый однофайловый HTML с последовательным чтением XLSX и ограниченным превью результатов и снимков
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
```
