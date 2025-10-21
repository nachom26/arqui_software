import socket
import sqlite3

SERVICE_NAME = 'sbase'  

print(f" INICIANDO SERVICIO BASE DE DATOS: {SERVICE_NAME}")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 5000))

conn = sqlite3.connect('sistema_archivos.db')
cursor = conn.cursor()

# Tablas básicas
cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios(   
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                email TEXT UNIQUE,
                contraseña TEXT,
                rol TEXT,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS historial (
        id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
        accion TEXT NOT NULL,
        fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        usuario TEXT NOT NULL,
        entidad_afectada TEXT NOT NULL
    )''')

cursor.execute('''
            CREATE TABLE IF NOT EXISTS carpeta(
                id_carpeta INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                propietario INTEGER REFERENCES usuarios(id_usuario),
                carpeta_padre INTEGER REFERENCES carpeta(id_carpeta) ON DELETE CASCADE,
                UNIQUE(nombre, propietario)
            )''')

cursor.execute('''
            CREATE TABLE IF NOT EXISTS archivo(   
                id_archivo INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo TEXT NOT NULL,
                tamaño INTEGER NOT NULL,
                fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
                propietario INTEGER REFERENCES usuarios(id_usuario),
                visibilidad TEXT,
                carpeta INTEGER REFERENCES carpeta(id_carpeta) ON DELETE CASCADE,
                ruta TEXT NOT NULL,
                UNIQUE(nombre, propietario)
            )''')

# Insertar datos de prueba
cursor.execute("SELECT COUNT(*) FROM historial")
if cursor.fetchone()[0] == 0:
    cursor.executemany(
        'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
        [
            ('Inicio de sesión', '1', 'Sistema'),
            ('Subida de archivo', '1', 'documento.pdf'),
            ('Búsqueda realizada', '1', 'archivos'),
        ]
    )
    conn.commit()

# Registrar servicio
sinit_msg = b'00010sinit' + SERVICE_NAME.encode()
print(f" Registrando: {sinit_msg}")
sock.sendall(sinit_msg)

length = sock.recv(5)
if length:
    response = sock.recv(int(length))
    print(f" Confirmación: {response}")

print(f"🎯 {SERVICE_NAME} LISTO - Esperando mensajes...")

try:
    while True:
        print("⏳ Esperando mensaje...")
        length_data = sock.recv(5)
        
        if not length_data:
            print(" Conexión cerrada")
            break
            
        total_len = int(length_data)
        data = b''
        while len(data) < total_len:
            chunk = sock.recv(total_len - len(data))
            data += chunk

        print(f"📨 Mensaje recibido: {data}")
        
        # Manejar ambos formatos
        command = None
        payload = None
        
        if data.startswith(SERVICE_NAME.encode() + b'OK') and len(data) >= len(SERVICE_NAME) + 7:
            print("🔍 Formato 1: Con OK del bus")
            command_start = len(SERVICE_NAME) + 2
            if len(data) >= command_start + 5:
                command = data[command_start:command_start+5].decode()
                payload = data[command_start+5:].decode()
        
        elif data.startswith(SERVICE_NAME.encode()) and len(data) >= len(SERVICE_NAME) + 5:
            print("🔍 Formato 2: Directo (sin OK)")
            command = data[len(SERVICE_NAME):len(SERVICE_NAME)+5].decode()
            payload = data[len(SERVICE_NAME)+5:].decode()
        
        if command and payload:
            print(f"🔍 Comando: {command}, Payload: {payload}")
            
            if command == 'query':
                try:
                    parts = payload.split('|', 1)
                    sql = parts[0]
                    
                    if len(parts) > 1 and parts[1].strip():
                        params = eval(parts[1])
                    else:
                        params = []
                    
                    print(f"🔍 SQL: {sql}")
                    print(f"🔍 Parámetros: {params}")
                    
                    # Ejecutar consulta
                    if params:
                        cursor.execute(sql, params)
                    else:
                        cursor.execute(sql)
                    
                    # Procesar resultados
                    if sql.strip().upper().startswith('SELECT'):
                        results = cursor.fetchall()
                        print(f" Resultados: {len(results)} filas")
                        response_content = f'{results}'
                    else:
                        conn.commit()
                        response_content = f'{cursor.rowcount} filas afectadas'
                        
                except Exception as e:
                    print(f" Error: {e}")
                    response_content = f'ERR|{str(e)}'
                
                # Enviar respuesta SIN "OK"
                full_response = SERVICE_NAME + response_content
                response_msg = f'{len(full_response):05}'.encode() + full_response.encode()
                
                print(f"ENVIANDO RESPUESTA: {response_msg}")
                sock.sendall(response_msg)
                print(" Respuesta enviada exitosamente")
            else:
                print(f"Comando no reconocido: {command}")
        else:
            print(f"  Formato de mensaje no reconocido: {data}")
                
except Exception as e:
    print(f" Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    sock.close()
    conn.close()
    print("🔒 Cerrado")
