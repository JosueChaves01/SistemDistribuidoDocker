import os
import psutil
import time
import requests
import socket
from fastapi import FastAPI
from PIL import Image
from io import BytesIO
import uvicorn
import base64
import threading
from uuid import uuid4
import pika
import json
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

class RabbitMQConnection:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.connection = None
            cls._instance.channel = None
            cls._instance.last_attempt = 0
        return cls._instance
    
    def get_channel(self):
        if self.connection and self.connection.is_open:
            return self.channel
            
        # Reconectar si ha pasado más de 5 segundos desde el último intento
        if time.time() - self.last_attempt < 5:
            raise pika.exceptions.AMQPConnectionError("Esperando entre reconexiones")
            
        self.last_attempt = time.time()
        
        try:
            credentials = pika.PlainCredentials('myuser', 'mypassword')
            parameters = pika.ConnectionParameters(
                host='rabbitmq',
                credentials=credentials,
                heartbeat=30,  # 30 segundos de heartbeat
                blocked_connection_timeout=60,
                connection_attempts=3,
                retry_delay=5
            )
            
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='tareas', durable=True)
            self.channel.basic_qos(prefetch_count=1)
            
            return self.channel
            
        except Exception as e:
            self.connection = None
            self.channel = None
            raise pika.exceptions.AMQPConnectionError(f"Error de conexión: {str(e)}")

# Configuración
load_dotenv()
app = FastAPI()
COORDINATOR_IP = os.getenv('COORDINATOR_HOST', 'coordinator')
NODE_NAME = os.getenv('WORKER_NAME', f'worker-{socket.gethostname()}')

# Configuración de requests
def setup_requests_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.1)
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

session = setup_requests_session()

# Funciones de monitoreo
def get_resource_usage():
    return {
        "name": NODE_NAME,
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "net": psutil.net_io_counters().bytes_sent,
        "ip": socket.gethostbyname(socket.gethostname())
    }

def background_report():
    while True:
        try:
            session.post(f"http://{COORDINATOR_IP}:8000/report", 
                       json=get_resource_usage(),
                       timeout=2)
        except Exception as e:
            print(f"Report error: {e}")
        time.sleep(2)

# Procesamiento de tareas
def process_image_task(b64_data):
    try:
        img = Image.open(BytesIO(base64.b64decode(b64_data))).convert("L")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue().hex()
    except Exception as e:
        print(f"Image processing error: {e}")
        raise

def ejecutar_tarea(task):
    task_id = str(uuid4())
    try:
        # Notificar inicio
        session.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "working",
            "task_id": task_id
        })

        # Procesar imagen
        result_hex = process_image_task(task.get("image_data_b64"))
        
        # Enviar resultado
        session.post(f"http://{COORDINATOR_IP}:8000/result-image", json={
            "image": result_hex
        })

    except Exception as e:
        print(f"Task failed: {e}")
    finally:
        # Notificar finalización
        session.post(f"http://{COORDINATOR_IP}:8000/working", json={
            "name": NODE_NAME,
            "status": "idle",
            "task_id": None
        })

# RabbitMQ Consumer

def start_rabbitmq_consumer():
    while True:
        try:
            rabbit = RabbitMQConnection()
            channel = rabbit.get_channel()
            
            def callback(ch, method, properties, body):
                try:
                    task = json.loads(body)
                    ejecutar_tarea(task)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except json.JSONDecodeError:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                except Exception as e:
                    print(f"Error procesando tarea: {str(e)}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            
            channel.basic_consume(
                queue='tareas',
                on_message_callback=callback,
                auto_ack=False
            )
            
            print(" [*] Conexión establecida - Esperando mensajes...")
            channel.start_consuming()
            
        except pika.exceptions.ConnectionClosedByBroker:
            print(" [ℹ] Conexión cerrada por el broker. Reintentando...")
            time.sleep(5)
        except pika.exceptions.AMQPChannelError as err:
            print(f" [✗] Error de canal: {err}. Reiniciando...")
            time.sleep(5)
        except pika.exceptions.AMQPConnectionError:
            print(" [✗] Error de conexión. Reintentando en 5s...")
            time.sleep(5)
        except KeyboardInterrupt:
            print(" [ℹ] Deteniendo worker...")
            if rabbit.connection:
                rabbit.connection.close()
            break
# Inicialización
@app.on_event("startup")
def startup():
    # Registrar worker
    session.post(f"http://{COORDINATOR_IP}:8000/register", 
                json=get_resource_usage())
    
    # Iniciar reporter
    threading.Thread(target=background_report, daemon=True).start()
    
    # Iniciar consumidores
    with ThreadPoolExecutor(max_workers=4) as executor:
        for _ in range(4):
            executor.submit(start_rabbitmq_consumer)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)