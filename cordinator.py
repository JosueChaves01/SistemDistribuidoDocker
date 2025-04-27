from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Optional
from uuid import uuid4
import os, time, base64, json, pika
from contextlib import contextmanager

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

workers: Dict[str, dict] = {}

# Models
class ResourceReport(BaseModel):
    name: str
    cpu: float
    ram: float
    net: float
    ip: str

class WorkerStatus(BaseModel):
    name: str
    status: str
    task_id: Optional[str]

class ResultImage(BaseModel):
    image: str

# Worker endpoints
@app.post("/register")
def register_or_update_worker(data: ResourceReport):
    workers[data.name] = {**data.dict(), "last_seen": time.time()}
    return {"status": "registered/updated"}

@app.post("/working")
def update_worker_task(data: WorkerStatus):
    if data.name not in workers:
        raise HTTPException(status_code=404, detail="Worker not found")
    workers[data.name].update({
        "status": data.status,
        "task_id": data.task_id,
        "last_seen": time.time()
    })
    return {"status": "updated"}

@app.post("/report")
def update_node(data: ResourceReport):
    return register_or_update_worker(data)

@app.get("/workers")
def get_workers():
    return workers

@app.get("/queue_size")
def queue_size():
    return {"pending_tasks": get_queue_length()}

@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Imagen muy grande")

    b64_data = base64.b64encode(content).decode("utf-8")
    count = send_tasks_to_queue(b64_data)
    return {"status": "sent", "message": f"{count} tareas enviadas"}

# Result handling
@app.post("/result-image")
def receive_image(data: ResultImage):
    filename = f"{uuid4().hex}.png"
    path = os.path.join("results", filename)
    os.makedirs("results", exist_ok=True)

    # Descomenta esta línea para guardar la imagen si es necesario
    # with open(path, "wb") as f:
    #     f.write(bytes.fromhex(data.image))

    return {"status": "received", "filename": filename}

@app.get("/result/{filename}")
def get_result_image(filename: str):
    path = os.path.join("results", filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(path)

@contextmanager
def rabbitmq_channel():
    connection = None
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='100.120.111.9',  # <- IP Tailscale del servidor RabbitMQ
                port=5672,             # RabbitMQ usa por defecto el puerto 5672 para conexiones AMQP
                credentials=pika.PlainCredentials('myuser', 'mypassword')
            )
        )
        channel = connection.channel()
        yield channel
    finally:
        if connection and connection.is_open:
            connection.close()

def get_queue_length(queue_name='tareas') -> int:
    try:
        with rabbitmq_channel() as channel:
            q = channel.queue_declare(queue=queue_name, durable=True, passive=True)
            return q.method.message_count
    except Exception as e:
        print(f"Error al obtener tamaño de cola: {str(e)}")
        return -1

def send_tasks_to_queue(b64_data: str, count: int = 500) -> int:
    try:
        with rabbitmq_channel() as channel:
            channel.queue_declare(queue='tareas', durable=True)
            
            for _ in range(count):
                task = {
                    "task_type": "filter",
                    "filter": "bw",
                    "image_data_b64": b64_data,
                    "task_id": uuid4().hex
                }
                channel.basic_publish(
                    exchange='',
                    routing_key='tareas',
                    body=json.dumps(task),
                    properties=pika.BasicProperties(
                        delivery_mode=2  # Persistente
                    )
                )
            return count
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error enviando tareas: {str(e)}")
# Run
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
