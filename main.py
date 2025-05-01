from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
from uuid import uuid4
import json
import os
import schedule
import threading
import time
import pyttsx3
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
from utils import enviar_a_google_home, enviar_mensaje_a_google_home, generar_mp3, programar_tarea_cronica
# Inicializar Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_KEY_PATH"))
firebase_admin.initialize_app(cred)

db = firestore.client()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
now =datetime.now(timezone.utc)  # Convertir `now` a un datetime con zona horaria UTC

# Asegúrate que el directorio static/mensajes existe
os.makedirs('static/mensajes', exist_ok=True)
tts = pyttsx3.init()
scheduler = BackgroundScheduler()
scheduler.start()

TAREAS_FILE = "tareas.json"

# 📦 Modelo Pydantic
class Tarea(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    descripcion: str
    fecha: str
    repetir: Optional[bool] = False
    dias_semana: Optional[List[str]] = None

    @validator('fecha')
    def validar_fecha(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError("Formato de fecha inválido. Usa ISO 8601 (ej. 2025-04-26T08:00)")
        return v

    @validator('dias_semana', each_item=True)
    def validar_dias(cls, dia):
        dias_validos = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU']
        if dia not in dias_validos:
            raise ValueError(f"Día inválido: {dia}")
        return dia

# 📂 Manejo de tareas
def cargar_tareas():
    #try:
    #    with open(TAREAS_FILE, "r") as f:
    #        datos = json.load(f)
    #        return [Tarea(**t) for t in datos]
    #except (json.JSONDecodeError, FileNotFoundError):
    #    return []
    tareas_ref = db.collection('tareas')
    docs = tareas_ref.stream()
    tareas = []
    ##tareas = [Tarea(**doc.to_dict() | {'id': doc.id}) for doc in docs]
    for doc in docs:
        data = doc.to_dict() | {'id': doc.id}

        # ✅ Convertir `fecha` a string si es un objeto de datetime
        if isinstance(data.get("fecha"), datetime):
            data["fecha"] = data["fecha"].isoformat()

        # ✅ Asegurar que `dias_semana` es una lista
        if isinstance(data.get("dias_semana"), str):  # Si es un string, conviértelo en lista
            data["dias_semana"] = [data["dias_semana"]]

        tareas.append(Tarea(**data))

    #with current_app.app_context():
    return tareas

def guardar_tareas(tareas: List[Tarea]):
    #with open(TAREAS_FILE, "w") as f:
    #    json.dump([t.model_dump() for t in tareas], f, indent=4)
    for tarea in tareas:
        data = tarea.model_dump()
        db.collection('tareas').add(data)
    return {"mensaje": "Tarea creada"}

# 🔔 Notificador
def recordar_tarea(tarea: Tarea):
    tts = pyttsx3.init()
    nombre_archivo = f"recordatorio_{int(time.time())}.mp3"
    print("nombre de archivo: ", nombre_archivo)
    msg = f"Recordatorio: {tarea.descripcion}" 
    print("mensaje o recordatorio: ", msg)  
    generar_mp3(msg, nombre_archivo)
    enviar_mensaje_a_google_home(nombre_archivo)

# 🕒 Scheduler puntual
def programar_recordatorio(tarea: Tarea):
    fecha = datetime.fromisoformat(tarea.fecha)
    scheduler.add_job(recordar_tarea, 'date', run_date=fecha, args=[tarea], id=tarea.id)

# 🕒 Scheduler general
@app.on_event("startup")
def startup_event():
    tareas = cargar_tareas()
    now = datetime.now()
    for tarea in tareas:
        fecha = datetime.fromisoformat(tarea.fecha).replace(tzinfo=None)
        if fecha > now:
            programar_recordatorio(tarea)

# API endpoints
@app.get("/tareas")
def listar_tareas():
    return cargar_tareas()

@app.post("/tareas")
def crear_tarea(tarea: Tarea):
    tareas = cargar_tareas()
    ##nueva = tareas.dict(exclude_unset=False)
    tareas.append(tarea)
    guardar_tareas(tareas)
    programar_recordatorio(tarea)

    if tarea.repetir and tarea.dias_semana:
        programar_tarea_cronica(tarea)

    return tarea

@app.delete("/tareas/{tarea_id}")
def eliminar_tarea(tarea_id: str):
    tareas = cargar_tareas()
    nuevas = [t for t in tareas if t.id != tarea_id]
    if len(tareas) == len(nuevas):
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    guardar_tareas(nuevas)
    try:
        db.collection('tareas').document(tarea_id).delete()
        return jsonify({"mensaje": "Tarea eliminada"}), 200
    except:
        pass
    return {"mensaje": "Tarea eliminada"}

# 🔁 Cron scheduler con `schedule`
def iniciar_scheduler():
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)
    threading.Thread(target=run_schedule, daemon=True).start()



iniciar_scheduler()
