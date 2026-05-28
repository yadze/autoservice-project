Запуск проекта

1. Создать PostgreSQL базу:

CREATE DATABASE autoservice;

2. Выполнить init_db.sql

3. Установить библиотеки:

pip install -r requirements.txt

4. Запустить FastAPI:

uvicorn main:app --reload

5. Запустить Flask service:

python flask_service.py

6. Открыть сайт:

http://127.0.0.1:8000
