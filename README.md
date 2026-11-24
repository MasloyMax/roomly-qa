# Roomly QA

Проверки [демо-формы бронирования переговорных Roomly](https://rcsi-science.github.io/demo-roomly/): чек-лист, найденные баги и автотесты на Python + Playwright.

В форме найдены шесть багов: неверная длительность, прошедшее время сегодня, некорректная почта, разметка из имени в подтверждении, вчерашняя дата после полуночи и обрезание заголовка на ширине 821 px. В последнем прогоне автотестов — **6 passed, 5 xfailed**. Подробности и ограничения проверки есть в отчёте.

- [Чек-лист с результатами](docs/checklist.md)
- [Сценарии по техникам тест-дизайна](docs/scenarios.md)
- [Баги и скриншоты](docs/bugs.md)
- [Отчёт о проверке](docs/report.md)
- [Требования к форме и устройство тестов](docs/spec.md)

## Запуск через Docker

Нужен Docker с Docker Compose v2. Из корня проекта выполните:

```bash
docker compose run --build --rm tests
```

Образ содержит Python и Chromium, зависимости установятся при сборке.

## Запуск без Docker

Для локального запуска использовался Python 3.13. Команды для Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest
```

В Linux и macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m playwright install --with-deps chromium
.venv/bin/python -m pytest
```

По умолчанию тесты открывают опубликованную демо-страницу. Другой адрес можно передать через `--base-url` или переменную окружения `BASE_URL`; параметр командной строки имеет приоритет.

```powershell
.\.venv\Scripts\python.exe -m pytest --base-url http://localhost:8000
```

Для этого примера сначала запустите локальную копию формы в отдельном терминале из корня проекта:

```powershell
python -m http.server 8000
```

## Что проверяют автотесты

В наборе **11 проверок** с учётом параметров:

- открытие страницы, успешная бронь и отказ при превышении вместимости;
- отказ для встречи на 29 минут — BUG-01;
- два варианта имени с угловыми скобками и HTML — BUG-04;
- отказ вчерашней дате после полуночи без перезагрузки и контроль после перезагрузки — BUG-05;
- целый заголовок на ширинах 320, 820 и 821 px — BUG-06.

Обычные проверки бронирования используют 15 января 2030 года, 12:00 по Москве; встреча назначена на следующий день. В сценарии полуночи часы продвигаются с 23:59 до 00:01 вместе с таймерами страницы. Поэтому тесты не зависят от текущей даты.

Пять вариантов для BUG-01 и BUG-04–06 помечены `xfail(strict=True, raises=AssertionError)`. Они проверяют правильное поведение формы. Пока баги воспроизводятся, результат — `XFAIL`. После исправления соответствующий вариант даст `XPASS(strict)`, и его маркер нужно будет убрать. Контроли после перезагрузки и на ширинах 320/820 px проходят как обычные тесты. Сбои загрузки страницы, браузера или шрифтов остаются ошибками прогона.

## Отчёты и разбор падений

После запуска в `artifacts/` сохраняются:

- `junit.xml` — результаты тестов;
- `browser/` — скриншоты и trace при падениях.

Каталог не хранится в Git. GitHub Actions запускает тот же набор через Docker и сохраняет отчёты на 7 дней.

Чтобы воспроизвести BUG-01 без `xfail` и сохранить trace со скриншотом:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking.py::test_discovered_defect --runxfail --tracing on --screenshot on --output artifacts/bug-01 --junitxml artifacts/bug-01.xml
```

Пока форма принимает встречу на 29 минут, эта команда завершится с `FAIL`. Trace можно открыть так:

```powershell
.\.venv\Scripts\python.exe -m playwright show-trace artifacts/bug-01/tests-test-booking-py-test-discovered-defect-chromium/trace.zip
```

Новые сценарии BUG-04–06 с контрольными вариантами можно запустить отдельно:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_booking.py::test_name_is_displayed_as_text tests/test_booking.py::test_past_date_is_rejected_after_midnight tests/test_layout.py::test_heading_is_not_clipped --runxfail --tracing on --screenshot on --output artifacts/new-regressions/diagnostic/browser --junitxml artifacts/new-regressions/diagnostic/junit.xml
```

С `--runxfail` известные дефекты показываются как обычные `FAIL`; скриншоты и trace помогут разобрать результат. Проверка вёрстки ждёт загрузки шрифтов и измеряет границы текста, поэтому ей нужен доступ и к ресурсам страницы.
