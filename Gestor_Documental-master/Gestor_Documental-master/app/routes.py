# app/routes.py
import os
import uuid
import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, session
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask import current_app, send_from_directory
from werkzeug.utils import secure_filename
from .db import get_db_connection

routes_blueprint = Blueprint('routes', __name__)

## Creación de Login
@routes_blueprint.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        correo = request.form['username']
        contrasena = request.form['password']

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE correo_electronico = %s", (correo,))
            usuario = cursor.fetchone()
            conn.close()

            if usuario:
                if usuario['estado'].lower() == 'inactivo':
                    error = '⚠️ Usuario inactivo. Contacte con el administrador.'
                elif bcrypt.checkpw(contrasena.encode('utf-8'), usuario['contrasena'].encode('utf-8')):
                    session['usuario'] = usuario['nombre_completo']
                    session['rol'] = usuario['rol']
                    return redirect(url_for('routes.dashboard'))
                else:
                    error = '⚠️ Contraseña incorrecta.'
            else:
                error = '⚠️ Usuario no encontrado.'

        except Exception as e:
            error = f'❌ Error de base de datos: {e}'

    return render_template('login.html', error=error)

@routes_blueprint.route('/dashboard')
def dashboard():
    if 'usuario' in session:
        return render_template('dashboard.html', usuario=session['usuario'], rol=session['rol'])
    else:
        return redirect(url_for('routes.login'))

@routes_blueprint.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('routes.login'))


## Creación de formulario para ABM
@routes_blueprint.route('/crear_usuario', methods=['GET', 'POST'])
def crear_usuario():
    if 'rol' not in session or session['rol'] != 'Administrador':
        return redirect(url_for('routes.dashboard'))

    mensaje = None
    error = None

    if request.method == 'POST':
        nombre = request.form['nombre_completo']
        correo = request.form['correo_electronico']
        contrasena = request.form['contrasena']
        rol = request.form['rol']
        estado = request.form['estado']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            hashed_password = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("""
                INSERT INTO usuarios (nombre_completo, correo_electronico, contrasena, rol, estado)
                VALUES (%s, %s, %s, %s, %s)
            """, (nombre, correo, hashed_password.decode('utf-8'), rol, estado))
            conn.commit()
            conn.close()
            mensaje = "✅ Usuario creado exitosamente."
        except Exception as e:
            error = f"❌ Error al crear usuario: {e}"

    return render_template('crear_usuario.html', mensaje=mensaje, error=error)

##Listar usuarios
@routes_blueprint.route('/usuarios', methods=['GET'])
def listar_usuarios():
    if 'rol' not in session or session['rol'] != 'Administrador':
        return redirect(url_for('routes.login'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nombre_completo, correo_electronico, rol, estado FROM usuarios")
        usuarios = cursor.fetchall()
        conn.close()
    except Exception as e:
        usuarios = []
        flash(f"Error al obtener los usuarios: {e}", "danger")

    return render_template('usuarios.html', usuarios=usuarios)

##Cambiar estodos desactivar/activar
@routes_blueprint.route('/cambiar_estado/<int:id>', methods=['POST'])
def cambiar_estado(id):
    if 'rol' not in session or session['rol'] != 'Administrador':
        return redirect(url_for('routes.login'))

    nuevo_estado = request.form.get('estado')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET estado = %s WHERE id = %s", (nuevo_estado, id))
        conn.commit()
        conn.close()
        flash("✅ Estado actualizado correctamente", "success")
    except Exception as e:
        flash(f"❌ Error al actualizar el estado: {e}", "danger")

    return redirect(url_for('routes.listar_usuarios'))

# ALZAR ARHCIVOS----------------
# # Verifica extensiones permitidas
@routes_blueprint.route('/subir_documento', methods=['GET', 'POST'])
def subir_documento():
    if 'usuario' not in session:
        return redirect(url_for('routes.login'))

    mensaje = None
    error = None

    if request.method == 'POST':
        nombre_carpeta = request.form.get('nombre_carpeta', '').strip()
        if not nombre_carpeta:
            error = '❌ Debe ingresar un nombre para la carpeta.'
        else:
            # Sanear el nombre para evitar caracteres inválidos en el sistema de archivos
            carpeta_segura = secure_filename(nombre_carpeta)
            carpeta_path = os.path.join(current_app.config['UPLOAD_FOLDER'], carpeta_segura)
            os.makedirs(carpeta_path, exist_ok=True)

            if 'archivos' not in request.files:
                error = '❌ No se encontraron archivos en la solicitud.'
            else:
                archivos = request.files.getlist('archivos')
                if not archivos or archivos[0].filename == '':
                    error = '⚠️ No se seleccionaron archivos.'
                else:
                    archivos_subidos = []
                    for archivo in archivos:
                        if archivo and archivo.filename.lower().endswith('.pdf'):
                            filename = secure_filename(archivo.filename)
                            ruta_subida = os.path.join(carpeta_path, filename)
                            archivo.save(ruta_subida)
                            archivos_subidos.append(filename)
                        else:
                            flash(f"❌ El archivo {archivo.filename} no es PDF y fue omitido.", "warning")

                    if archivos_subidos:
                        mensaje = f'✅ Archivos subidos exitosamente en la carpeta: {carpeta_segura}'
                    else:
                        error = '❌ Ningún archivo válido fue subido.'

    return render_template('subir_documento.html', mensaje=mensaje, error=error)
# VER O DESCARGAR ARCHIVOS
@routes_blueprint.route('/documentos')
def ver_documento():
    if 'usuario' not in session:
        return redirect(url_for('routes.login'))

    upload_folder = current_app.config['UPLOAD_FOLDER']
    carpetas = []
    try:
        carpetas = [d for d in os.listdir(upload_folder) if os.path.isdir(os.path.join(upload_folder, d))]
    except Exception as e:
        flash(f"❌ No se pudieron cargar las carpetas: {e}", "danger")

    return render_template('documentos.html', carpetas=carpetas)


@routes_blueprint.route('/documentos/<carpeta>')
def ver_documentos_carpeta(carpeta):
    if 'usuario' not in session:
        return redirect(url_for('routes.login'))

    carpeta_path = os.path.join(current_app.config['UPLOAD_FOLDER'], carpeta)
    archivos = []
    try:
        archivos = [f for f in os.listdir(carpeta_path) if f.lower().endswith('.pdf')]
    except Exception as e:
        flash(f"❌ No se pudieron cargar los documentos de la carpeta: {e}", "danger")

    return render_template('documentos_carpeta.html', carpeta=carpeta, archivos=archivos)


@routes_blueprint.route('/uploads/<carpeta>/<nombre_archivo>')
def descargar_archivo(carpeta, nombre_archivo):
    if 'usuario' not in session:
        return redirect(url_for('routes.login'))
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], carpeta)
    return send_from_directory(upload_folder, nombre_archivo)