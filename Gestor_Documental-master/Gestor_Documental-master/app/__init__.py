# app/__init__.py
import os
from flask import Flask
from .routes import routes_blueprint  # ✅ Importación correcta del Blueprint

def create_app():
    app = Flask(__name__)
    app.secret_key = 'tu_clave_secreta'

    app.register_blueprint(routes_blueprint)
        # Configuración para subir archivos
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB máximo
    app.config['ALLOWED_EXTENSIONS'] = {'pdf'}  # Solo PDFs permitidos

    # Crear carpeta uploads si no existe
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])       

    return app