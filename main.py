from flask import Flask
from flask_restx import Api
from dotenv import load_dotenv
import os

load_dotenv()

from src.infrastructure.inbound.http.routes.clase_routes import ns as clase_ns
from src.infrastructure.inbound.http.middlewares.error_handler import registrar_error_handlers

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')

# Swagger
api = Api(
    app,
    version     = '1.0',
    title       = 'Clase IA API',
    description = 'API para automatización de clases con IA como profesor',
    doc         = '/swagger/'
)

api.add_namespace(clase_ns)
registrar_error_handlers(app)


@app.route('/health')
def health():
    return {"status": "ok", "version": "1.0"}, 200


if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', True))