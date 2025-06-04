from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import current_app

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    imagen = db.Column(db.String(255))
    categoria = db.Column(db.String(50), nullable=False, index=True)
    stock = db.Column(db.Integer, nullable=False, default=0)
    descripcion = db.Column(db.Text, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    fecha_creacion = db.Column(db.DateTime, default=db.func.now())
    fecha_actualizacion = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    subproductos = db.relationship('Subproducto', backref='producto', lazy=True, cascade='all, delete-orphan')

    @hybrid_property
    def stock_disponible(self):
        return max(0, self.stock)
    
    @classmethod
    def crear(cls, datos):
        """Método para crear un nuevo producto"""
        producto = cls(
            nombre=datos['nombre'],
            slug=cls.generar_slug(datos['nombre']),
            precio=datos['precio'],
            categoria=datos['categoria'],
            stock=datos.get('stock', 0),
            descripcion=datos['descripcion']
        )
        
        if 'imagen' in datos:
            producto.imagen = datos['imagen']
            
        db.session.add(producto)
        return producto
    
    @classmethod
    def actualizar(cls, producto_id, datos):
        """Método para actualizar un producto existente"""
        producto = cls.query.get_or_404(producto_id)
        
        producto.nombre = datos['nombre']
        producto.precio = datos['precio']
        producto.categoria = datos['categoria']
        producto.stock = datos.get('stock', 0)
        producto.descripcion = datos['descripcion']
        producto.fecha_actualizacion = datetime.utcnow()
        
        if 'imagen' in datos:
            if producto.imagen:
                cls.eliminar_imagen(producto.imagen)
            producto.imagen = datos['imagen']
        elif datos.get('eliminar_imagen', False):
            if producto.imagen:
                cls.eliminar_imagen(producto.imagen)
            producto.imagen = None
            
        return producto
    
    @classmethod
    def guardar_imagen(cls, archivo_imagen):
        """Guarda una imagen en el sistema de archivos"""
        if not archivo_imagen:
            return None
            
        nombre_seguro = secure_filename(archivo_imagen.filename)
        nombre_unico = f"{datetime.now().timestamp()}_{nombre_seguro}"
        ruta_guardado = os.path.join(current_app.config['UPLOAD_FOLDER'], nombre_unico)
        
        archivo_imagen.save(ruta_guardado)
        return f"/uploads/{nombre_unico}"

    @classmethod
    def eliminar_imagen(cls, ruta_imagen):
        """Elimina una imagen del sistema de archivos"""
        if not ruta_imagen:
            return
            
        nombre_archivo = ruta_imagen.replace('/uploads/', '')
        ruta_completa = os.path.join(current_app.config['UPLOAD_FOLDER'], nombre_archivo)
        
        if os.path.exists(ruta_completa):
            os.remove(ruta_completa)

    @classmethod
    def generar_slug(cls, nombre):
        """Genera un slug único para el producto"""
        from slugify import slugify
        slug_base = slugify(nombre)
        slug_unico = slug_base
        contador = 1
        
        while cls.query.filter_by(slug=slug_unico).first() is not None:
            slug_unico = f"{slug_base}-{contador}"
            contador += 1
            
        return slug_unico
    
    def __repr__(self):
        return f'<Producto {self.nombre}>'

class Subproducto(db.Model):
    __tablename__ = 'subproductos'
    
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    precio_extra = db.Column(db.Numeric(10, 2), default=0.00)
    sku = db.Column(db.String(50), unique=True)
    stock = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<Subproducto {self.nombre} del Producto {self.producto_id}>'