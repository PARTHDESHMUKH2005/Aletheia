"""ASGI adapter for API Gateway; the worker is dispatched separately."""
from mangum import Mangum
from app.main import app

handler = Mangum(app, lifespan="off")
