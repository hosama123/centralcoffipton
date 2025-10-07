from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'clave_secreta_segura'

# Configuración de la base de datos
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ventas",
        port=3306
    )
    cursor = db.cursor(dictionary=True)
    print("✅ Conexión a la base de datos exitosa")
except mysql.connector.Error as err:
    print(f"❌ Error de conexión a la base de datos: {err}")
    exit(1)

# ----------------------------
# Decoradores de seguridad
# ----------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('⚠️ Debes iniciar sesión.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def rol_required(rol_id):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'id_rol' not in session:
                flash('⚠️ Debes iniciar sesión.', 'warning')
                return redirect(url_for('login'))
            if session.get('id_rol') != rol_id:
                flash('⛔ Acceso denegado. No tienes permisos suficientes.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
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
# Rutas de Autenticación
# ----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('name')
        email = request.form.get('email')
        password_raw = request.form.get('password')
        confirm = request.form.get('confirm')

        if not nombre or not email or not password_raw or not confirm:
            flash('⚠️ Todos los campos son obligatorios.', 'warning')
            return render_template('register.html')

        if password_raw != confirm:
            flash('⚠️ Las contraseñas no coinciden.', 'warning')
            return render_template('register.html')

        try:
            cursor.execute("SELECT * FROM usuario WHERE email = %s", (email,))
            if cursor.fetchone():
                flash('❌ El correo ya está registrado.', 'danger')
                return render_template('register.html')

            password_hash = generate_password_hash(password_raw)

            cursor.execute("INSERT INTO usuario (nombre, email, password, id_rol) VALUES (%s, %s, %s, %s)",
                           (nombre, email, password_hash, 2))
            db.commit()
            flash('✅ Registro exitoso. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'❌ Error en el registro: {str(e)}', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario' in session:
        if session.get('id_rol') == 1:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('usuario'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('⚠️ Todos los campos son obligatorios.', 'warning')
            return render_template('login.html')

        try:
            cursor.execute("SELECT * FROM usuario WHERE email = %s", (email,))
            usuario = cursor.fetchone()

            if usuario:
                print(f"DEBUG: Usuario encontrado: {usuario['email']}")
                print(f"DEBUG: ID Rol: {usuario['id_rol']}")
                
                if check_password_hash(usuario['password'], password):
                    session['usuario'] = usuario['nombre']
                    session['email'] = usuario['email']
                    session['id'] = usuario['id']
                    session['id_rol'] = usuario['id_rol']
                    flash(f'✅ Bienvenido, {usuario["nombre"]}', 'success')
                    
                    if usuario['id_rol'] == 1:
                        print("DEBUG: Redirigiendo a admin")
                        return redirect(url_for('admin'))
                    else:
                        print("DEBUG: Redirigiendo a usuario")
                        return redirect(url_for('usuario'))
                else:
                    print("DEBUG: Contraseña incorrecta")
                    flash('❌ Credenciales incorrectas.', 'danger')
            else:
                print("DEBUG: Usuario no encontrado")
                flash('❌ Credenciales incorrectas.', 'danger')
                
        except Exception as e:
            print(f"DEBUG: Error en login: {str(e)}")
            flash(f'❌ Error en el inicio de sesión: {str(e)}', 'danger')
    
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
    try:
        cursor.execute("SELECT COUNT(*) as total FROM producto")
        total_productos = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM pedido")
        total_pedidos = cursor.fetchone()['total']
        
        cursor.execute("SELECT COUNT(*) as total FROM usuario WHERE id_rol = 2")
        total_usuarios = cursor.fetchone()['total']
        
        print(f"DEBUG: Estadísticas - Productos: {total_productos}, Pedidos: {total_pedidos}, Usuarios: {total_usuarios}")
        
        return render_template('admin.html', 
                             total_productos=total_productos,
                             total_pedidos=total_pedidos,
                             total_usuarios=total_usuarios)
    except Exception as e:
        flash(f'❌ Error al cargar el panel de administración: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/usuario')
@login_required
@rol_required(2)
def usuario():
    try:
        cursor.execute("SELECT * FROM producto WHERE stock > 0")
        productos = cursor.fetchall()
        return render_template('usuario.html', productos=productos)
    except Exception as e:
        flash(f'❌ Error al cargar productos: {str(e)}', 'danger')
        return redirect(url_for('index'))

# ----------------------------
# CRUD PRODUCTOS (solo Admin)
# ----------------------------
@app.route('/productos')
@login_required
@rol_required(1)
def listar_productos():
    try:
        cursor.execute("SELECT * FROM producto ORDER BY id DESC")
        productos = cursor.fetchall()
        return render_template('productos.html', productos=productos)
    except Exception as e:
        flash(f'❌ Error al cargar productos: {str(e)}', 'danger')
        return redirect(url_for('admin'))

@app.route('/productos/agregar', methods=['GET', 'POST'])
@login_required
@rol_required(1)
def agregar_producto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        
        if not nombre or not precio or not stock:
            flash('⚠️ Todos los campos son obligatorios.', 'warning')
            return render_template('agregar_producto.html')
        
        try:
            cursor.execute("INSERT INTO producto (nombre, precio, stock) VALUES (%s, %s, %s)",
                           (nombre, float(precio), int(stock)))
            db.commit()
            flash('✅ Producto agregado correctamente', 'success')
            return redirect(url_for('listar_productos'))
        except Exception as e:
            flash(f'❌ Error al agregar producto: {str(e)}', 'danger')
            return render_template('agregar_producto.html')
    
    return render_template('agregar_producto.html')

@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@rol_required(1)
def editar_producto(id):
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        
        if not nombre or not precio or not stock:
            flash('⚠️ Todos los campos son obligatorios.', 'warning')
            return redirect(url_for('editar_producto', id=id))
        
        try:
            cursor.execute("UPDATE producto SET nombre=%s, precio=%s, stock=%s WHERE id=%s",
                           (nombre, float(precio), int(stock), id))
            db.commit()
            flash('✏️ Producto actualizado correctamente', 'info')
            return redirect(url_for('listar_productos'))
        except Exception as e:
            flash(f'❌ Error al actualizar producto: {str(e)}', 'danger')
            return redirect(url_for('editar_producto', id=id))
    
    try:
        cursor.execute("SELECT * FROM producto WHERE id=%s", (id,))
        producto = cursor.fetchone()
        if not producto:
            flash('❌ Producto no encontrado', 'danger')
            return redirect(url_for('listar_productos'))
        
        return render_template('editar_producto.html', producto=producto)
    except Exception as e:
        flash(f'❌ Error al cargar producto: {str(e)}', 'danger')
        return redirect(url_for('listar_productos'))

@app.route('/productos/eliminar/<int:id>')
@login_required
@rol_required(1)
def eliminar_producto(id):
    try:
        cursor.execute("SELECT * FROM producto WHERE id=%s", (id,))
        producto = cursor.fetchone()
        if not producto:
            flash('❌ Producto no encontrado', 'danger')
            return redirect(url_for('listar_productos'))

        cursor.execute("SELECT COUNT(*) as total FROM pedido WHERE id_producto = %s", (id,))
        tiene_pedidos = cursor.fetchone()['total']
        
        if tiene_pedidos > 0:
            flash('❌ No se puede eliminar el producto porque tiene pedidos asociados', 'danger')
        else:
            cursor.execute("DELETE FROM producto WHERE id=%s", (id,))
            db.commit()
            flash('🗑️ Producto eliminado correctamente', 'success')
    except Exception as e:
        flash(f'❌ Error al eliminar producto: {str(e)}', 'danger')
    
    return redirect(url_for('listar_productos'))

# ----------------------------
# CRUD PEDIDOS
# ----------------------------
@app.route('/pedidos')
@login_required
def listar_pedidos():
    try:
        if session['id_rol'] == 1:
            cursor.execute("""
                SELECT p.id, u.nombre AS usuario, pr.nombre AS producto, p.cantidad, p.fecha
                FROM pedido p
                JOIN usuario u ON p.id_usuario = u.id
                JOIN producto pr ON p.id_producto = pr.id
                ORDER BY p.fecha DESC
            """)
        else:
            cursor.execute("""
                SELECT p.id, pr.nombre AS producto, p.cantidad, p.fecha
                FROM pedido p
                JOIN producto pr ON p.id_producto = pr.id
                WHERE p.id_usuario = %s
                ORDER BY p.fecha DESC
            """, (session['id'],))
        
        pedidos = cursor.fetchall()
        return render_template('pedidos.html', pedidos=pedidos)
    except Exception as e:
        flash(f'❌ Error al cargar pedidos: {str(e)}', 'danger')
        if session['id_rol'] == 1:
            return redirect(url_for('admin'))
        else:
            return redirect(url_for('usuario'))

@app.route('/pedidos/agregar/<int:producto_id>', methods=['POST'])
@login_required
@rol_required(2)
def agregar_pedido(producto_id):
    try:
        cantidad = int(request.form.get('cantidad', 0))
        
        if cantidad <= 0:
            flash('❌ La cantidad debe ser mayor a 0', 'danger')
            return redirect(url_for('usuario'))

        cursor.execute("SELECT stock, nombre FROM producto WHERE id=%s", (producto_id,))
        producto = cursor.fetchone()
        
        if not producto:
            flash('❌ Producto no encontrado', 'danger')
            return redirect(url_for('usuario'))
            
        if producto['stock'] < cantidad:
            flash(f'❌ Stock insuficiente. Solo hay {producto["stock"]} unidades disponibles', 'danger')
            return redirect(url_for('usuario'))

        cursor.execute("INSERT INTO pedido (id_usuario, id_producto, cantidad) VALUES (%s, %s, %s)",
                       (session['id'], producto_id, cantidad))
        cursor.execute("UPDATE producto SET stock = stock - %s WHERE id=%s", (cantidad, producto_id))
        db.commit()

        flash('✅ Pedido realizado correctamente', 'success')
        return redirect(url_for('listar_pedidos'))
        
    except Exception as e:
        flash(f'❌ Error al realizar pedido: {str(e)}', 'danger')
        return redirect(url_for('usuario'))

if __name__ == '__main__':
    app.run(debug=True)