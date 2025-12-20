Что реализовано и как

1. REST API (CRUD)
   Сделано по лекционному шаблону, с соблюдением REST-семантики:

GET /tasks - список всех задач
GET /tasks/{id} - получение по ID
POST /tasks - создание
PATCH /tasks/{id} - частичное обновление через exclude_unset=True
DELETE /tasks/{id} - удаление
Все эндпоинты используют AsyncSession, работают с моделью TaskModel, возвращают Pydantic-схемы.

2. WebSocket /ws/tasks
   Реализован ConnectionManager:

connect() / disconnect()
broadcast(message) - рассылает события при любом изменении задачи
Поддерживаемые события:
task_created - с task_id, title
task_updated - с task_id
task_deleted - с task_id
WebSocket-соединение устойчиво (обработка WebSocketDisconnect добавлена).

3. Фоновая задача
   Запускается автоматически при старте (@app.on_event("startup") -> asyncio.create_task(periodic_task_generator()))
   Каждые 60 секунд делает асинхронный HTTP-запрос к https://jsonplaceholder.typicode.com/todos
   Импортирует 1 задачу, сохраняет её через AsyncSession
   Данные маппятся:
   title <- item["title"]
   description <- "generated" (фиксировано: «наполняет базу данными, полученными со стороннего сайта»)
   done <- item["completed"]
4. Ручной запуск фоновой задачи
   Эндпоинт POST /task-generator/run добавляет задачу в BackgroundTasks.

5. Асинхронная работа с БД
   Используется sqlite+aiosqlite:///./tasks.db
   AsyncEngine, AsyncSession, await db.execute(select(...)) - полностью асинхронно
   Таблица создаётся при старте через conn.run_sync(Base.metadata.create_all)
