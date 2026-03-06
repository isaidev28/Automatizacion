from flask import Flask
from flask_restx import Api, Resource, fields
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Configuración de Swagger
api = Api(
    app,
    version='1.0',
    title='Mi API',
    description='Documentación de mi API',
    doc='/swagger/'
)

# Namespace para clases
ns = api.namespace('clases', description='Operaciones de clases')


@app.route('/')
def home():
    return {"message": "API funcionando"}

if __name__ == '__main__':
    app.run(debug=True)
