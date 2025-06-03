from flask import Flask, render_template, request, redirect, session, url_for
from models import db, Producto
from flask_session import Session

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
    ids = session.get("carrito", [])
    productos = Producto.query.filter(Producto.id.in_(ids)).all() if ids else []
    return render_template("carrito.html", productos=productos)

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

@app.route('/producto/nuevo', methods=['GET', 'POST'])
@admin_required
def nuevo_producto():
    if request.method == 'POST':
        p = Producto(nombre=request.form['nombre'], precio=request.form['precio'], imagen=request.form['imagen'])
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin_panel'))
    return render_template('form_producto.html')

@app.route('/producto/editar/<int:id>', methods=['GET', 'POST'])
@admin_required
def editar_producto(id):
    p = Producto.query.get_or_404(id)
    if request.method == 'POST':
        p.nombre = request.form['nombre']
        p.precio = request.form['precio']
        p.imagen = request.form['imagen']
        db.session.commit()
        return redirect(url_for('admin_panel'))
    return render_template('form_producto.html', producto=p)

@app.route('/producto/eliminar/<int:id>')
@admin_required
def eliminar_producto(id):
    p = Producto.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(debug=True)
