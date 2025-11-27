import csv, json, random, os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, time
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dotenv import load_dotenv 
from database import UserAttempt, Winner, get_db

load_dotenv()

SECRET_SALT = os.getenv("SECRET_SALT", "default_salt_if_missing")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

if not GOOGLE_CLIENT_ID:
    print("GOOGLE_CLIENT_ID не знайдено в .env")

try:
    ACTIVE_START_HOUR = int(os.getenv("ACTIVE_START_HOUR", "9"))
    ACTIVE_END_HOUR = int(os.getenv("ACTIVE_END_HOUR", "17"))
except ValueError:
    ACTIVE_START_HOUR = 9
    ACTIVE_END_HOUR = 17

ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "rcit.ukr.education")

origins_env = os.getenv("ALLOWED_ORIGINS", "")
origins = [origin.strip() for origin in origins_env.split(",")] if origins_env else ["*"]

DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

app = FastAPI(debug=DEBUG_MODE)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

try:
    with open('prizes.json', 'r', encoding="utf-8") as f:
        Prizes_config = json.load(f)
        Prizes_dict = {item['day']: item for item in Prizes_config}
except FileNotFoundError:
    print("prizes.json не знайдено")
    Prizes_dict = {}


def get_secret_time_for_day(day: int) -> time:
    seed_value = f"{SECRET_SALT}_day_{day}"
    random.seed(seed_value) 
    hour = random.randint(ACTIVE_START_HOUR, ACTIVE_END_HOUR - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    print(hour, minute, second)
    return time(hour, minute, second)

def verify_google_token(token: str) -> str:
    try:
        id_info = id_token.verify_oauth2_token(token, google_requests.Request(), GOOGLE_CLIENT_ID)
        email = id_info['email']
        return email
    except Exception:
        raise HTTPException(status_code=401, detail="Помилка авторизації")

class TryLuckRequest(BaseModel):
    day: int        
    token: str 

class HistoryRequest(BaseModel):
    token: str


def log_winner_to_file(day, email, prize):
    try:
        with open('winners.csv', 'a', newline='', encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([day, email, prize, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    except Exception:
        pass

@app.get("/", response_class=HTMLResponse)
async def read_root():
    file_path = os.path.join(BASE_DIR, "main.html")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        safe_client_id = GOOGLE_CLIENT_ID if GOOGLE_CLIENT_ID else ""
        content = content.replace("{{GOOGLE_CLIENT_ID}}", safe_client_id)
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Помилка: main.html не знайдено!</h1>", status_code=500)

@app.post("/try-luck")
def try_luck(request: TryLuckRequest, db: Session = Depends(get_db)):
    user_email = verify_google_token(request.token)
    
    if not user_email.endswith(f"@{ALLOWED_DOMAIN}"):
         raise HTTPException(status_code=403, detail=f"Доступ тільки для {ALLOWED_DOMAIN}")

    day_config = Prizes_dict.get(request.day)
    if not day_config:
        raise HTTPException(status_code=404, detail="День не знайдено")

    current_day_of_month = datetime.now().day

    # щоб протестувати вікриття ячейок на фронті просто закоментуй цю перевірку днів (до try)
    if request.day < current_day_of_month:
        return {
            "status": "INFO", 
            "title": "Архів 📜", 
            "message": day_config.get('text', 'Цей день вже минув.'),
            "prize": None
        }

    try:
        attempt = UserAttempt(stud_email=user_email, day=request.day)
        db.add(attempt)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "ALREADY_OPENED", "message": "Ти вже відкривав це віконце сьогодні!"}

    response = {
        "status": "INFO", 
        "title": "Мудрість дня ✨",
        "message": day_config.get('text', 'Бажаємо гарного дня!'),
        "prize": None
    }

    prize_name = day_config.get('prize')
    
    if prize_name:
        existing_winner = db.query(Winner).filter(Winner.day == request.day).first()
        
        if not existing_winner:
            target_time = get_secret_time_for_day(request.day)
            current_time = datetime.now().time()
            
            if current_time >= target_time:
                new_winner = Winner(
                    day=request.day,
                    stud_email=user_email, 
                    prize_name=prize_name
                )
                db.add(new_winner)
                try:
                    db.commit()
                    log_winner_to_file(request.day, user_email, prize_name)
                    
                    response["status"] = "WIN_PRIZE"
                    response["title"] = "🎉 НЕЙМОВІРНО! 🎉"
                    response["message"] = "Ти сьогоднішній щасливчик!"
                    response["prize"] = prize_name
                except IntegrityError:
                    db.rollback()
                    pass

    return response


@app.post("/get-history")
def get_user_history(request: HistoryRequest, db: Session = Depends(get_db)):
    try:
        user_email = verify_google_token(request.token)
    except Exception:
        return []

    attempts = db.query(UserAttempt).filter(UserAttempt.stud_email == user_email).all()
    return [attempt.day for attempt in attempts]

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)