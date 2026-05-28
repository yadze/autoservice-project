import hashlib
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from jose import jwt
from starlette.requests import Request
import db
print(db.MASTER_DSN)

SECRET = "mysecret"
ALGO = "HS256"
security = HTTPBearer()
app = FastAPI()
templates = Jinja2Templates(directory="static/templates")

class User(BaseModel):
    username: str
    password: str

class ServiceIn(BaseModel):
    title: str
    description: str
    price: int

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def token(user_id):
    expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET, ALGO)

def get_user(credentials=Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGO])
        user = db.query("SELECT id, username FROM users WHERE id=%s", (payload["sub"],), fetch=True)
        if not user:
            raise HTTPException(401)
        return user
    except:
        raise HTTPException(401)

@app.post("/api/register")
def register(u: User):
    if db.query("SELECT id FROM users WHERE username=%s", (u.username,), fetch=True):
        raise HTTPException(400, "User exists")
    db.query("INSERT INTO users (username, password_hash) VALUES (%s,%s)",
             (u.username, hash_pw(u.password)), mode='master')
    return {"ok": True}

@app.post("/api/login")
def login(u: User):
    user = db.query("SELECT id, password_hash FROM users WHERE username=%s", (u.username,), fetch=True)
    if not user or user["password_hash"] != hash_pw(u.password):
        raise HTTPException(401, "Invalid")
    access_token = token(user["id"])
    refresh_token = jwt.encode({"sub": str(user["id"]), "exp": datetime.now(timezone.utc) + timedelta(days=7)}, SECRET, ALGO)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.post("/api/refresh")
def refresh(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET, algorithms=[ALGO])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401)
        new_access = jwt.encode({"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(minutes=30)}, SECRET, ALGO)
        return {"access_token": new_access}
    except:
        raise HTTPException(401)

@app.get("/api/users/me")
def me(current_user=Depends(get_user)):
    return current_user

@app.get("/user/{username}")
def get_user_info(username: str, current_user=Depends(get_user)):
    if current_user["username"] != username:
        raise HTTPException(403, "Not your profile")
    return {"username": current_user["username"], "id": current_user["id"]}

@app.get("/api/services")
def list_services(search: str = None, sort: str = "id", page: int = 1, limit: int = 10):
    allowed = ["id", "title", "price"]
    if sort not in allowed:
        sort = "id"
    order_dir = "ASC"
    where = f"WHERE title ILIKE '%%{search}%%'" if search else ""
    sql = f"""
        SELECT id, title, description, price
        FROM services
        {where}
        ORDER BY {sort} {order_dir}
        LIMIT %s OFFSET %s
    """
    items = db.query(sql, (limit, (page - 1) * limit), fetch='all')
    count_sql = f"SELECT COUNT(*) as cnt FROM services {where}"
    total = db.query(count_sql, fetch=True)["cnt"]
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total else 1
    }

@app.post("/api/services")
def create_service(s: ServiceIn, _=Depends(get_user)):
    new = db.query(
        "INSERT INTO services (title,description,price) VALUES (%s,%s,%s) RETURNING *",
        (s.title, s.description, s.price), mode='master', fetch=True
    )
    return new

@app.put("/api/services/{sid}")
def update_service(sid: int, s: ServiceIn, _=Depends(get_user)):
    db.query(
        "UPDATE services SET title=%s, description=%s, price=%s WHERE id=%s",
        (s.title, s.description, s.price, sid), mode='master'
    )
    return db.query("SELECT * FROM services WHERE id=%s", (sid,), fetch=True)

@app.delete("/api/services/{sid}")
def delete_service(sid: int, _=Depends(get_user)):
    db.query("DELETE FROM services WHERE id=%s", (sid,), mode='master')
    return {"deleted": sid}

@app.get("/api/orders")
def my_orders(current_user=Depends(get_user), page: int = 1, limit: int = 10):
    offset = (page - 1) * limit
    items = db.query(
        "SELECT o.*, s.title as service_title FROM orders o JOIN services s ON o.service_id=s.id WHERE o.user_id=%s ORDER BY o.id DESC LIMIT %s OFFSET %s",
        (current_user["id"], limit, offset), fetch='all'
    )
    total = db.query("SELECT COUNT(*) as cnt FROM orders WHERE user_id=%s", (current_user["id"],), fetch=True)["cnt"]
    return {"items": items, "total": total}

@app.post("/api/orders")
def create_order(service_id: int, current_user=Depends(get_user)):
    db.query(
        "INSERT INTO orders (user_id, service_id) VALUES (%s,%s)",
        (current_user["id"], service_id), mode='master'
    )
    return {"ok": True}

@app.delete("/api/orders/{oid}")
def cancel_order(oid: int, current_user=Depends(get_user)):
    db.query("DELETE FROM orders WHERE id=%s AND user_id=%s", (oid, current_user["id"]), mode='master')
    return {"deleted": oid}

@app.get("/api/dashboard")
def dashboard_data(_=Depends(get_user)):
    data = db.query(
        "SELECT s.title, COUNT(o.id) as cnt FROM services s LEFT JOIN orders o ON s.id=o.service_id GROUP BY s.id",
        fetch='all'
    )
    return {"labels": [d["title"] for d in data], "values": [d["cnt"] for d in data]}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/hash/{s}")
def hash_str(s: str):
    return {"request": s, "result": hashlib.sha256(s.encode()).hexdigest()}

import json
from pathlib import Path

@app.get("/api/about")
def api_about():
    about_path = Path("static/about.json")
    if about_path.exists():
        with open(about_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"name": "AutoService", "version": "1.0", "description": "Full-stack автосервис"}

@app.get("/about", response_class=HTMLResponse)
def about_page(req: Request):
    return templates.TemplateResponse("about.html", {"request": req})

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request})

@app.get("/{username}")
def get_user_by_username(username: str, current_user=Depends(get_user)):
    if current_user["username"] != username:
        raise HTTPException(403, "Not your profile")
    orders = db.query(
        "SELECT o.id, s.title, o.created_at FROM orders o JOIN services s ON o.service_id=s.id WHERE o.user_id=%s",
        (current_user["id"],), fetch='all'
    )
    return {"username": current_user["username"], "id": current_user["id"], "orders": orders}
