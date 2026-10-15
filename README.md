# Управление студентами — DevOps, вариант 8

СРО 1: CI/CD приложения управления студентами.
СРО 2: веб-приложение и PostgreSQL в Docker Compose.

## Назначение проекта

Приложение хранит ФИО, группу и email студента. Реализованы добавление,
просмотр, изменение и удаление записей. Для первого локального запуска
используется SQLite. При запуске через Docker Compose используется PostgreSQL.
В архив входят исходники, автоматические тесты и конфигурации для обеих СРО.
Результаты и скриншоты необходимо сохранить после собственного запуска.

## Локальный запуск

Требуется Python 3.12 или новее. В Windows можно дважды щёлкнуть
`START_WINDOWS.cmd`: скрипт создаст `.venv`, установит зависимости
и запустит приложение. Дождитесь адреса http://127.0.0.1:5000 в окне.

Те же действия вручную в PowerShell из папки проекта:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m flask --app wsgi run
```

Открыть http://127.0.0.1:5000. Для Linux: `python3 -m venv .venv`,
затем `source .venv/bin/activate`, остальные команды аналогичны.
SQLite используется только для локальной проверки; файл `students.db`
создаётся автоматически. API поддерживает GET/POST /api/students и
GET/PUT/DELETE /api/students/{id}. /health проверяет соединение с БД.

## Тесты и локальная проверка конвейера

Откройте второе окно PowerShell в папке проекта:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

Для двух полных локальных прогонов:

```powershell
.\.venv\Scripts\python.exe scripts/run_local_ci.py --run-id run-01 --version 1.0.0
.\.venv\Scripts\python.exe scripts/run_local_ci.py --run-id run-02 --version 1.0.1
```

Локальные журналы сохраняются в `evidence/run-01` и `evidence/run-02`.
Второй прогон проверяет ту же кодовую базу с другим APP_VERSION.
Это два отдельных исполнения, а не две разные редакции исходного кода.
Локальные прогоны не заменяют два запуска GitHub Actions.

## Docker Compose с PostgreSQL

Нужен запущенный Docker Desktop с Linux-контейнерами и Docker Compose v2.

```powershell
Copy-Item .env.example .env
# При необходимости изменить POSTGRES_PASSWORD в .env
docker compose config
docker compose up -d --build --wait
docker compose ps
curl.exe http://127.0.0.1:5000/health
docker compose logs --tail=30 web db
docker compose down
docker compose up -d --wait
```

В `/health` ожидается `database: postgresql`; до перезапуска следует
создать запись и после него проверить её сохранность. `down` сохраняет
именованный том. `docker compose down -v` удаляет данные и не нужен
для обычного завершения работы. База не публикует порт наружу.
Пароль в `.env.example` — пример только для учебной среды.

## GitHub Actions

Создать собственный репозиторий, добавить проект, выполнить push в main.
Полная конфигурация находится в `.github/workflows/ci.yml`.
Конвейер выполняет lint, тесты, упаковку и при push в main запускает
артефакт во временной тестовой среде runner, затем останавливает сервер.
Постоянного хостинга данный workflow не создаёт.
Для требования «два запуска GitHub Actions» необходимо выполнить два push
и сохранить реальные ссылки и скриншоты вкладки Actions.

## Ограничения учебного приложения

Авторизация и разграничение ролей не реализованы. Вводите только учебные
данные. Контейнер публикует приложение на 127.0.0.1. Базовая проверка email
не проверяет существование почтового ящика. Обновление таблиц при развитии
схемы потребует миграций; create_all подходит для начального учебного запуска.
