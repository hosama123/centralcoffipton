from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import time

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura_central_cofi_2025'

# ----------------------------
# Configuración de conexión simple
# ----------------------------
DB_CONFIG = {
    'host': "bb8lmg848rlzdah1tkd1-mysql.services.clever-cloud.com",
    'user': "uurszqwfnysdkfip",
    'password': "RhxKt5priED0BOS7L2KO",
    'database': "bb8lmg848rlzdah1tkd1",
    'port': 3306,
    'autocommit': True
}

def get_db_connection():
    """Obtiene una conexión simple a la base de datos"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        print(f"❌ Error de conexión: {e}")
        return None

def execute_query(query, params=None, fetch=False, fetch_one=False):
    """
    Ejecuta una consulta de manera segura
    - fetch=True: para SELECT que retornan múltiples filas
    - fetch_one=True: para SELECT que retornan una sola fila
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch:
            result = cursor.fetchall()
        elif fetch_one:
            result = cursor.fetchone()
        else:
            connection.commit()
            result = cursor.rowcount if cursor.rowcount != -1 else True
            
        return result
        
    except Error as e:
        print(f"❌ Error en consulta: {e}")
        if connection:
            connection.rollback()
        return None
    finally:
        # Cerrar recursos siempre
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

# ----------------------------
# Decoradores
# ----------------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario' not in session:
            flash('⚠️ Debes iniciar sesión.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def rol_required(rol_id):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'id_rol' not in session or session['id_rol'] != rol_id:
                flash('⛔ Acceso denegado.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ----------------------------
# Rutas Públicas
# ----------------------------
@app.route('/')
def index():
    cards = [
        {'img': 'https://picsum.photos/seed/cafe1/300/200', 'title': 'Café Premium', 'text': 'Café de alta calidad de las mejores regiones'},
        {'img': 'https://picsum.photos/seed/cafe2/300/200', 'title': 'Café Orgánico', 'text': '100% natural y sostenible'},
        {'img': 'https://picsum.photos/seed/cafe3/300/200', 'title': 'Café Especial', 'text': 'Sabores únicos y aromáticos'},
        {'img': 'https://picsum.photos/seed/cafe4/300/200', 'title': 'Mezclas Exclusivas', 'text': 'Blends especiales artesanales'}
    ]
    return render_template('index.html', cards=cards)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# ----------------------------
# Autenticación
# ----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('name')
        email = request.form.get('email')
        password_raw = request.form.get('password')
        confirm = request.form.get('confirm')

        if not all([nombre, email, password_raw, confirm]):
            flash('⚠️ Todos los campos son obligatorios.', 'warning')
            return render_template('register.html')

        if password_raw != confirm:
            flash('⚠️ Las contraseñas no coinciden.', 'warning')
            return render_template('register.html')

        # Verificar si el email ya existe
        existing_user = execute_query(
            "SELECT id FROM usuario WHERE email = %s", 
            (email,), 
            fetch_one=True
        )
        
        if existing_user:
            flash('❌ El correo ya está registrado.', 'danger')
            return render_template('register.html')

        # Registrar nuevo usuario
        password_hash = generate_password_hash(password_raw)
        result = execute_query(
            "INSERT INTO usuario (nombre, email, password, id_rol) VALUES (%s, %s, %s, %s)",
            (nombre, email, password_hash, 1)  # Rol 2 = usuario administrador por defecto
            
        )
        
        if result:
            flash('✅ Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('❌ Error en el registro. Intenta nuevamente.', 'danger')
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        return redirect(url_for('admin') if session.get('id_rol') == 1 else url_for('usuario'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('⚠️ Todos los campos son obligatorios.', 'warning')
            return render_template('login.html')

        usuario = execute_query(
            "SELECT * FROM usuario WHERE email = %s", 
            (email,), 
            fetch_one=True
        )
        
        if usuario and check_password_hash(usuario['password'], password):
            session['usuario'] = usuario['nombre']
            session['email'] = usuario['email']
            session['id'] = usuario['id']
            session['id_rol'] = usuario['id_rol']
            flash(f'✅ Bienvenido, {usuario["nombre"]}', 'success')
            return redirect(url_for('admin') if usuario['id_rol'] == 1 else url_for('usuario'))
        else:
            flash('❌ Credenciales incorrectas.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 Sesión cerrada correctamente.', 'info')
    return redirect(url_for('index'))

# ----------------------------
# Paneles
# ----------------------------
@app.route('/admin')
@login_required
@rol_required(1)
def admin():
    # Obtener estadísticas
    total_productos = execute_query("SELECT COUNT(*) as total FROM producto", fetch_one=True)
    total_pedidos = execute_query("SELECT COUNT(*) as total FROM pedido", fetch_one=True)
    total_usuarios = execute_query("SELECT COUNT(*) as total FROM usuario WHERE id_rol = 2", fetch_one=True)

    if not all([total_productos, total_pedidos, total_usuarios]):
        flash('❌ Error al cargar estadísticas.', 'danger')
        return redirect(url_for('index'))

    return render_template('admin.html', 
                         total_productos=total_productos['total'],
                         total_pedidos=total_pedidos['total'], 
                         total_usuarios=total_usuarios['total'])

@app.route('/usuario')
@login_required
@rol_required(2)
def usuario():
    productos = execute_query("SELECT * FROM producto WHERE stock > 0 ORDER BY nombre", fetch=True)
    
    if productos is None:
        flash('❌ Error al cargar productos.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('usuario.html', productos=productos)

# ----------------------------
# CRUD Productos
# ----------------------------
@app.route('/productos')
@login_required
@rol_required(1)
def listar_productos():
    productos = execute_query("SELECT * FROM producto ORDER BY id DESC", fetch=True)
    
    if productos is None:
        flash('❌ Error al cargar productos.', 'danger')
        return redirect(url_for('admin'))
        
    return render_template('productos.html', productos=productos)

@app.route('/productos/agregar', methods=['GET', 'POST'])
@login_required
@rol_required(1)
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        descripcion = request.form.get('descripcion', '')

        if not all([nombre, precio, stock]):
            flash('⚠️ Nombre, precio y stock son obligatorios.', 'warning')
            return render_template('agregar_producto.html')

        try:
            precio_float = float(precio)
            stock_int = int(stock)
        except ValueError:
            flash('❌ Precio y stock deben ser números válidos.', 'danger')
            return render_template('agregar_producto.html')

        result = execute_query(
            "INSERT INTO producto (nombre, precio, stock, descripcion) VALUES (%s, %s, %s, %s)",
            (nombre, precio_float, stock_int, descripcion)
        )
        
        if result:
            flash('✅ Producto agregado correctamente', 'success')
            return redirect(url_for('listar_productos'))
        else:
            flash('❌ Error al agregar producto.', 'danger')
            
    return render_template('agregar_producto.html')

@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required(1)
def editar_producto(id):
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        descripcion = request.form.get('descripcion', '')
        
        if not all([nombre, precio, stock]):
            flash('⚠️ Nombre, precio y stock son obligatorios.', 'warning')
            return redirect(url_for('editar_producto', id=id))

        try:
            precio_float = float(precio)
            stock_int = int(stock)
        except ValueError:
            flash('❌ Precio y stock deben ser números válidos.', 'danger')
            return redirect(url_for('editar_producto', id=id))
        
        result = execute_query(
            "UPDATE producto SET nombre = %s, precio = %s, stock = %s, descripcion = %s WHERE id = %s",
            (nombre, precio_float, stock_int, descripcion, id)
        )
        
        if result:
            flash('✅ Producto actualizado correctamente', 'success')
            return redirect(url_for('listar_productos'))
        else:
            flash('❌ Error al actualizar producto.', 'danger')
    
    producto = execute_query("SELECT * FROM producto WHERE id = %s", (id,), fetch_one=True)
    
    if not producto:
        flash('❌ Producto no encontrado.', 'danger')
        return redirect(url_for('listar_productos'))
        
    return render_template('editar_producto.html', producto=producto)

@app.route('/productos/eliminar/<int:id>')
@login_required
@rol_required(1)
def eliminar_producto(id):
    result = execute_query("DELETE FROM producto WHERE id = %s", (id,))
    
    if result:
        flash('✅ Producto eliminado correctamente', 'success')
    else:
        flash('❌ Error al eliminar producto.', 'danger')
    
    return redirect(url_for('listar_productos'))

# ----------------------------
# CRUD Usuarios
# ----------------------------
@app.route('/usuarios')
@login_required
@rol_required(1)
def listar_usuarios():
    usuarios = execute_query("SELECT * FROM usuario ORDER BY id DESC", fetch=True)
    
    if usuarios is None:
        flash('❌ Error al cargar usuarios.', 'danger')
        return redirect(url_for('admin'))
        
    return render_template('listar_usuarios.html', usuarios=usuarios)

@app.route('/usuarios/agregar', methods=['POST'])
@login_required
@rol_required(1)
def agregar_usuario():
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password_raw = request.form.get('password')
    id_rol = request.form.get('id_rol', 2)

    if not all([nombre, email, password_raw]):
        flash('⚠️ Todos los campos son obligatorios.', 'warning')
        return redirect(url_for('listar_usuarios'))

    # Verificar si el email ya existe
    existing_user = execute_query(
        "SELECT id FROM usuario WHERE email = %s", 
        (email,), 
        fetch_one=True
    )
    
    if existing_user:
        flash('❌ El correo ya está registrado.', 'danger')
        return redirect(url_for('listar_usuarios'))

    password_hash = generate_password_hash(password_raw)
    result = execute_query(
        "INSERT INTO usuario (nombre, email, password, id_rol) VALUES (%s, %s, %s, %s)",
        (nombre, email, password_hash, int(id_rol))
    )
    
    if result:
        flash('✅ Usuario agregado correctamente', 'success')
    else:
        flash('❌ Error al agregar usuario.', 'danger')
    
    return redirect(url_for('listar_usuarios'))

@app.route('/usuarios/editar/<int:id>', methods=['POST'])
@login_required
@rol_required(1)
def editar_usuario(id):
    nombre = request.form.get('nombre')
    email = request.form.get('email')
    password_raw = request.form.get('password')
    id_rol = request.form.get('id_rol', 2)

    if not all([nombre, email]):
        flash('⚠️ Nombre y email son obligatorios.', 'warning')
        return redirect(url_for('listar_usuarios'))

    if password_raw:
        password_hash = generate_password_hash(password_raw)
        result = execute_query(
            "UPDATE usuario SET nombre = %s, email = %s, password = %s, id_rol = %s WHERE id = %s",
            (nombre, email, password_hash, int(id_rol), id)
        )
    else:
        result = execute_query(
            "UPDATE usuario SET nombre = %s, email = %s, id_rol = %s WHERE id = %s",
            (nombre, email, int(id_rol), id)
        )
    
    if result:
        flash('✅ Usuario actualizado correctamente', 'success')
    else:
        flash('❌ Error al actualizar usuario.', 'danger')
    
    return redirect(url_for('listar_usuarios'))

@app.route('/usuarios/eliminar/<int:id>')
@login_required
@rol_required(1)
def eliminar_usuario(id):
    # No permitir eliminar al propio usuario
    if session.get('id') == id:
        flash('❌ No puedes eliminar tu propio usuario.', 'danger')
        return redirect(url_for('listar_usuarios'))
    
    result = execute_query("DELETE FROM usuario WHERE id = %s", (id,))
    
    if result:
        flash('✅ Usuario eliminado correctamente', 'success')
    else:
        flash('❌ Error al eliminar usuario.', 'danger')
    
    return redirect(url_for('listar_usuarios'))

# ----------------------------
# Gestión de Pedidos
# ----------------------------
@app.route('/pedidos')
@login_required
def listar_pedidos():
    if session.get('id_rol') == 1:  # Admin ve todos los pedidos
        pedidos = execute_query("""
            SELECT p.*, u.nombre as usuario_nombre, pr.nombre as producto_nombre 
            FROM pedido p 
            JOIN usuario u ON p.id_usuario = u.id 
            JOIN producto pr ON p.id_producto = pr.id 
            ORDER BY p.fecha DESC
        """, fetch=True)
    else:  # Usuario normal ve solo sus pedidos
        pedidos = execute_query("""
            SELECT p.*, pr.nombre as producto_nombre 
            FROM pedido p 
            JOIN producto pr ON p.id_producto = pr.id 
            WHERE p.id_usuario = %s 
            ORDER BY p.fecha DESC
        """, (session['id'],), fetch=True)
    
    if pedidos is None:
        flash('❌ Error al cargar pedidos.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('pedidos.html', pedidos=pedidos)

@app.route('/pedidos/agregar/<int:producto_id>', methods=['POST'])
@login_required
@rol_required(2)
def agregar_pedido(producto_id):
    cantidad = request.form.get('cantidad', 1)
    
    try:
        cantidad_int = int(cantidad)
        if cantidad_int <= 0:
            raise ValueError
    except ValueError:
        flash('⚠️ La cantidad debe ser un número válido mayor a 0.', 'warning')
        return redirect(url_for('usuario'))

    # Verificar stock
    producto = execute_query(
        "SELECT nombre, stock FROM producto WHERE id = %s", 
        (producto_id,), 
        fetch_one=True
    )
    
    if not producto:
        flash('❌ Producto no encontrado.', 'danger')
        return redirect(url_for('usuario'))
        
    if producto['stock'] < cantidad_int:
        flash(f'❌ Stock insuficiente. Solo quedan {producto["stock"]} unidades.', 'danger')
        return redirect(url_for('usuario'))

    # Crear pedido
    result = execute_query(
        "INSERT INTO pedido (id_usuario, id_producto, cantidad, fecha) VALUES (%s, %s, %s, %s)",
        (session['id'], producto_id, cantidad_int, datetime.now())
    )
    
    if result:
        # Actualizar stock
        execute_query(
            "UPDATE producto SET stock = stock - %s WHERE id = %s",
            (cantidad_int, producto_id)
        )
        flash('✅ Pedido realizado correctamente', 'success')
    else:
        flash('❌ Error al realizar pedido.', 'danger')
    
    return redirect(url_for('usuario'))

# ----------------------------
# Manejo de errores
# ----------------------------
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

@app.errorhandler(mysql.connector.Error)
def handle_db_error(error):
    flash('❌ Error de base de datos. Por favor, intenta nuevamente.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    print("🚀 Iniciando servidor CentralCofi...")
    print("📊 Configuración de base de datos optimizada")
    print("🔧 Conexiones individuales sin pool")
    print("🔄 Manejo robusto de errores")
    print("📍 Servidor ejecutándose en http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)