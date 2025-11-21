1. Створення віртуального оточення 
python -m venv .venv
.venv\Scripts\activate
2. Встановлення залежностей
pip install -r requirements.txt
3. Налаштування env
4. Запуск сервера
uvicorn main:app --reload

-Щоб змінюати дні в календарі, перейдіть у main.html і там через змінну *currentDay* і там задавайте дні-