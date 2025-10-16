import socket
import sqlite3

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bus_addr = ('localhost', 5000)
sock.connect(bus_addr)
conn = sqlite3.connect('archivador.db')
cursor = conn.cursor()

cursor.execute('''
            CREATE TABLE IF NOT EXISTS carpeta(
                id_carpeta INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                propietario INTEGER REFERENCES usuarios(id_usuario),
                carpeta_padre INTEGER REFERENCES carpeta(id_carpeta)
            )''')

cursor.execute('''
            CREATE TABLE IF NOT EXISTS archivo(   
                id_archivo INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                tipo TEXT UNIQUE,
                tamaño INTEGER,
                fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
                propietario INTEGER REFERENCES usuarios(id_usuario),
                visibilidad TEXT,
                carpeta INTEGER REFERENCES carpeta(id_carpeta),
                ruta TEXT
            )''')

try:
    service = 'sarch'
    message = b'00010sinit' + service.encode()
    sock.sendall(message)
    sinit = 1

    while True:
        print('Esperando mensaje...')
        amount_received = 0
        amount_expected = int(sock.recv (5))

        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)

        if sinit == 1:
            sinit = 0
            print('Servicio iniciado')
            continue
        
        elif data[:5].decode() == 'sarch':
            print('Mensaje recibido:', data)
            comando = data[5:15].decode()
            payload = data[15:].decode()

            if comando == 'createfold':
                try:
                    nombre, propietario, carpeta_padre = payload.split('|')
                    cursor.execute('INSERT INTO carpeta (nombre, propietario, carpeta_padre) VALUES (?, ?, ?)', 
                                   (nombre, propietario, carpeta_padre))
                    conn.commit()
                    response = 'OK|Carpeta creada'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'
            

            elif comando == 'deletefold':
                try:
                    carpeta_id = payload
                    cursor.execute('DELETE FROM carpeta WHERE id_carpeta = ?', (carpeta_id,))
                    conn.commit()
                    response = 'OK|Carpeta eliminada'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'listfiles':
                try:
                    propietario = payload
                    cursor.execute('SELECT * FROM archivo WHERE propietario = ?', (propietario,))
                    archivos = cursor.fetchall()
                    archivos_str = '|'.join([f'{a[0]},{a[1]},{a[2]},{a[3]},{a[4]},{a[5]},{a[6]},{a[7]}' for a in archivos])
                    response = f'OK|{archivos_str}'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'listfolders':
                try:
                    propietario = payload
                    cursor.execute('SELECT * FROM carpeta WHERE propietario = ?', (propietario,))
                    carpetas = cursor.fetchall()
                    carpetas_str = '|'.join([f'{c[0]},{c[1]},{c[2]},{c[3]}' for c in carpetas])
                    response = f'OK|{carpetas_str}'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'deletefile':
                try:
                    archivo_id = payload
                    cursor.execute('DELETE FROM archivo WHERE id_archivo = ?', (archivo_id,))
                    conn.commit()
                    response = 'OK|Archivo eliminado'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'uploadfile':
                try:
                    nombre, tipo, tamaño, propietario, visibilidad, carpeta, ruta = payload.split('|')
                    cursor.execute('INSERT INTO archivo (nombre, tipo, tamaño, propietario, visibilidad, carpeta, ruta) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                                   (nombre, tipo, tamaño, propietario, visibilidad, carpeta, ruta))
                    conn.commit()
                    response = 'OK|Archivo subido'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'
            
            elif comando == 'downloadfile':
                try:
                    archivo_id = payload
                    cursor.execute('SELECT * FROM archivo WHERE id_archivo = ?', (archivo_id,))
                    archivo = cursor.fetchone()
                    if archivo:
                        archivo_str = f'{archivo[0]},{archivo[1]},{archivo[2]},{archivo[3]},{archivo[4]},{archivo[5]},{archivo[6]},{archivo[7]}'
                        response = f'OK|{archivo_str}'
                    else:
                        response = 'ERR|Archivo no encontrado'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'renamefile':
                try:
                    archivo_id, nuevo_nombre = payload.split('|')
                    cursor.execute('UPDATE archivo SET nombre = ? WHERE id_archivo = ?', (nuevo_nombre, archivo_id))
                    conn.commit()
                    response = 'OK|Archivo renombrado'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'movefile':
                try:
                    archivo_id, nueva_carpeta = payload.split('|')
                    cursor.execute('UPDATE archivo SET carpeta = ? WHERE id_archivo = ?', (nueva_carpeta, archivo_id))
                    conn.commit()
                    response = 'OK|Archivo movido'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            

            else:
                response = 'ERR|Comando no reconocido'

            response_message = f'{len(response):05}{service}{response}'.encode()
            sock.sendall(response_message)
            print('Respuesta enviada:', response_message)


finally:
    conn.close()
    sock.close()


