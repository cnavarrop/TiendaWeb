import os
import re
import unicodedata
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from models import db, Producto
from flask_session import Session
from collections import Counter
 


def generar_slug(nombre):
    # Normaliza acentos y caracteres especiales
    nombre = unicodedata.normalize('NFKD', nombre).encode('ascii', 'ignore').decode('utf-8')
    nombre = re.sub(r'[^\w\s-]', '', nombre).strip().lower()
    return re.sub(r'[-\s]+', '-', nombre)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['SECRET_KEY'] = 'clave_super_secreta'
app.config['SESSION_TYPE'] = 'filesystem'

db.init_app(app)
Session(app)

with app.app_context():
    db.create_all()

# ------------------------ RUTAS DE TIENDA ------------------------

@app.route('/')
def index():
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)


@app.route('/agregar/<int:id>')
def agregar_al_carrito(id):
    session.setdefault("carrito", []).append(id)
    session.modified = True
    return redirect(url_for('index'))

@app.route('/carrito')
def ver_carrito():
    ids = list(map(int, session.get("carrito", [])))  # Convertir strings a int
    if not ids:
        return render_template("carrito.html", carrito=[], total=0)

    cantidades = Counter(ids)
    productos = Producto.query.filter(Producto.id.in_(cantidades.keys())).all()

    carrito = []
    total = 0
    for p in productos:
        cantidad = cantidades[p.id]
        subtotal = cantidad * p.precio
        total += subtotal
        carrito.append({
            "id": p.id,
            "nombre": p.nombre,
            "imagen": p.imagen,
            "precio": p.precio,
            "cantidad": cantidad,
            "subtotal": subtotal
        })
    
    return render_template("carrito.html", carrito=carrito, total=total)

@app.route('/vaciar_carrito')
def vaciar_carrito():
    session.pop("carrito", None)
    return redirect(url_for('index'))

# ------------------------ ADMIN (PROTEGIDO) ------------------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['password'] == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_panel'))
        return "Contraseña incorrecta"
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

def admin_required(f):
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/admin')
@admin_required
def admin_panel():
    productos = Producto.query.all()
    return render_template('productos_admin.html', productos=productos)
@app.route('/admin/productos')
@admin_required  # Decorador para verificar sesión admin
def admin_productos():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Productos por página
    query = request.args.get('q', '')

    # Base de la consulta
    if query:
        productos_query = Producto.query.filter(
            Producto.nombre.ilike(f'%{query}%')
        )
    else:
        productos_query = Producto.query

    # Paginación
    productos = productos_query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('productos_admin.html', 
                         productos=productos.items,
                         pagination=productos,
                         query=query)

@app.route('/producto/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_producto():
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            precio = float(request.form['precio'])
            stock = int(request.form['stock'])
            descripcion = request.form['descripcion']
            categoria = request.form['categoria']
            imagen_file = request.files.get('imagen')

            # Ruta por defecto en caso de que no se suba imagen
            imagen_url = '/static/img/default.jpg'

            # Procesar imagen si fue subida
            if imagen_file and imagen_file.filename:
                filename = secure_filename(imagen_file.filename)
                ruta_relativa = os.path.join('static/uploads', filename)
                imagen_file.save(ruta_relativa)
                imagen_url = '/' + ruta_relativa.replace('\\', '/')
            slug= generar_slug(nombre)

            nuevo = Producto(
                nombre=nombre,
                slug = slug,
                precio=precio,
                imagen=imagen_url,
                stock=stock,
                descripcion=descripcion,
                categoria=categoria
            )
            db.session.add(nuevo)
            db.session.commit()
            return redirect(url_for('admin_panel'))

        except Exception as e:
            return f"Error al guardar producto: {e}", 400

    return render_template('form_producto.html')


@app.route('/producto/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_producto(id):
    producto = Producto.query.get_or_404(id)

    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            slug = generar_slug(nombre)
            precio = float(request.form['precio'])
            stock = int(request.form['stock'])
            descripcion = request.form['descripcion']
            categoria = request.form['categoria']

            # Imagen actual
            imagen_file = request.files.get('imagen')
            eliminar_imagen = request.form.get('eliminar_imagen')

            # Si se sube una nueva imagen, la usamos
            if imagen_file and imagen_file.filename:
                filename = secure_filename(imagen_file.filename)
                ruta_relativa = os.path.join('static/uploads', filename)
                imagen_file.save(ruta_relativa)
                imagen_url = '/' + ruta_relativa.replace('\\', '/')
                producto.imagen = imagen_url

            # Si se marca el checkbox "eliminar imagen"
            elif eliminar_imagen:
                producto.imagen = '/static/img/default.jpg'

            # Actualizar otros campos
            producto.nombre = nombre
            producto.slug = slug
            producto.precio = precio
            producto.stock = stock
            producto.descripcion = descripcion
            producto.categoria = categoria

            db.session.commit()
            return redirect(url_for('admin_panel'))

        except Exception as e:
            return f"Error al editar producto: {e}", 400

    return render_template('form_producto.html', producto=producto)

@app.route('/producto/eliminar/<int:id>')
@admin_required
def eliminar_producto(id):
    p = Producto.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)


@app.route('/api/agregar/<int:id>')
def api_agregar_al_carrito(id):
    carrito = session.get("carrito", [])
    carrito.append(id)
    session["carrito"] = carrito
    session.modified = True

    # Contar total de productos en carrito
    total_carrito = len(carrito)

    return jsonify({"mensaje": "Producto agregado", "total_carrito": total_carrito})

@app.context_processor
def inject_total_carrito():
    return {'total_carrito': session.get('total_carrito', 0)}