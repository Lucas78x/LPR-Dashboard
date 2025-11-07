import os, io, csv, hashlib, secrets, time
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import create_auth_db, get_user, create_user, list_alarms, add_alarm, delete_alarm
from models import importar_csv_mem, filtrar_registros_mem, resumo_mem, estatisticas

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Pastas
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Sessão (cookies assinados)
SECRET_KEY = os.environ.get("APP_SECRET", secrets.token_hex(32))
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Inicialização ---
create_auth_db()

# cria usuário padrão (admin/admin123) se não existir
def sha256_hash(password: str, salt: str = "salzinho"):
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

# Usuários iniciais e senhas fortes
default_users = {
    "lucas": "sn7Ee8bC9ozR",
    "andre": "cU4bV3yN1rT2",
    "flavio": "pQ9zR7eW5tA8",
    "rildo": "nK6xL2mV4bS9",
    "wallef": "dH3qT8rZ6jP5"
}

for username, password in default_users.items():
    if not get_user(username):
        create_user(username, sha256_hash(password))

# ---------- Cache de CSV ----------
CSV_PATH = "placas.csv"
CSV_LAST_MOD = 0
APP_REGS = []

def load_csv_if_changed():
    """Recarrega CSV apenas se o arquivo for modificado."""
    global APP_REGS, CSV_LAST_MOD
    if not os.path.exists(CSV_PATH):
        APP_REGS = []
        return
    mod_time = os.path.getmtime(CSV_PATH)
    if mod_time != CSV_LAST_MOD:
        CSV_LAST_MOD = mod_time
        APP_REGS = importar_csv_mem(CSV_PATH)
        print(f"🔄 CSV recarregado ({len(APP_REGS)} registros)")

# ---------- Cache de alarmes ----------
ALARMS_CACHE = []
ALARMS_LAST_READ = 0

def get_cached_alarms(ttl: int = 60):
    """Recarrega alarmes a cada 60 segundos (TTL)."""
    global ALARMS_CACHE, ALARMS_LAST_READ
    now = time.time()
    if now - ALARMS_LAST_READ > ttl:
        ALARMS_CACHE = list_alarms()
        ALARMS_LAST_READ = now
    return ALARMS_CACHE

# ---------- Auth ----------
@app.get("/login")
async def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login")
async def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = get_user(username)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Usuário ou senha inválidos"})
    uid, uname, pwd_hash = user
    if sha256_hash(password) != pwd_hash:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Usuário ou senha inválidos"})
    request.session["user"] = uname
    return RedirectResponse(url="/", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

def ensure_login(request: Request):
    """Redireciona para /login caso o usuário não esteja autenticado."""
    if not request.session.get("user"):
        response = RedirectResponse(url="/login", status_code=303)
        response.delete_cookie("session")
        return response
    return None

# ---------- Dashboard ----------
@app.get("/")
async def dashboard(request: Request, placa: str | None = None, regiao: str | None = None, data: str | None = None):
    redirect = ensure_login(request)
    if redirect:
        return redirect

    load_csv_if_changed()

    registros = filtrar_registros_mem(APP_REGS, placa, regiao, data)
    info = resumo_mem(registros)
    regioes = sorted(list({r["regiao"] for r in APP_REGS if r.get("regiao")}))
    stats = estatisticas(registros)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": request.session.get("user"),
        "registros": registros[-200:],  # limita a 200 linhas para carregar rápido
        "placa": placa or "",
        "regiao": regiao or "Todos",
        "data": data or "",
        "resumo": info,
        "regioes": regioes,
        "stats": stats
    })

# ---------- API: Registros (AJAX leve) ----------
@app.get("/api/registros")
async def api_registros(request: Request):
    redirect = ensure_login(request)
    if redirect:
        return redirect
    load_csv_if_changed()
    return JSONResponse({"registros": APP_REGS[-100:]})  # apenas os últimos 100 registros

# ---------- Export CSV filtrado ----------
@app.get("/exportar_csv")
async def exportar_csv(placa: str | None = None, regiao: str | None = None, data: str | None = None, request: Request = None):
    if request and not request.session.get("user"):
        return RedirectResponse(url="/login", status_code=302)

    load_csv_if_changed()
    registros = filtrar_registros_mem(APP_REGS, placa, regiao, data)
    headers = list(registros[0].keys()) if registros else [
        "indice", "pista", "tam_kb", "datahora", "nplaca", "marca", "cor_placa",
        "cor_veiculo", "veloc_kmh", "regiao", "tipo_evento", "tamanho_veiculo"
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    for r in registros:
        writer.writerow(r)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=registros_filtrados.csv"}
    )

# ---------- Alarmes ----------
@app.get("/alarms")
async def alarms_page(request: Request):
    redirect = ensure_login(request)
    if redirect:
        return redirect
    alarms = get_cached_alarms()
    return templates.TemplateResponse("alarms.html", {"request": request, "alarms": alarms})

@app.post("/alarms/add")
async def alarms_add(request: Request, car_name: str = Form(...), plate: str = Form(...)):
    redirect = ensure_login(request)
    if redirect:
        return redirect
    add_alarm(car_name.strip(), plate.strip().upper())
    return RedirectResponse(url="/alarms", status_code=302)

@app.post("/alarms/delete")
async def alarms_delete(request: Request, id: int = Form(...)):
    redirect = ensure_login(request)
    if redirect:
        return redirect
    delete_alarm(id)
    return RedirectResponse(url="/alarms", status_code=302)

# ---------- API: Alarmes ----------
@app.get("/api/alarms")
async def api_alarms(request: Request):
    """Retorna todas as placas configuradas como alarmes em cache (sem recarregar o BD a cada requisição)."""
    redirect = ensure_login(request)
    if redirect:
        return redirect

    alarms = get_cached_alarms()

    return {
        "alarms": [
            {
                "id": a.get("id"),
                "car_name": a.get("car_name", "Veículo"),
                "plate": a.get("plate", "").upper()
            }
            for a in alarms
        ]
    }
