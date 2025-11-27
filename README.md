1. Створення віртуального оточення 

python -m venv .venv
.venv\Scripts\activate

2. Встановлення залежностей

pip install -r requirements.txt

3. Налаштування env

4. Запуск сервера

uvicorn main:app --reload / або просто python main.py

-Щоб змінюати дні в календарі, перейдіть у main.html і там через змінну *currentDay* і там задавайте дні-


--DOCKER--

docker build -t advcalendar .


docker run -d --env-file .env -p 8000:8000 advcalendar


там має бути файл з тими хто виграв, то щоб його отримати з контейнера

docker cp <container_id>:/app/winners.csv ./winners.csv
