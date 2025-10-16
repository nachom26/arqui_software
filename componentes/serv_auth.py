import socket
import sqlite3

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

bus_addr = ('localhost', 5000)
sock.connect(bus_addr)

conn = sqlite3.connect('archivador.db')
cursor = conn.cursor()
cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios(   
                id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                email TEXT UNIQUE,
                contraseña TEXT,
                rol TEXT,
                fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')

try:

    service = 'sauth'

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
        
        elif data[:5].decode() == 'sauth':
            print('Mensaje recibido:', data)
            comando = data[5:10].decode()
            payload = data[10:].decode()

            if comando == 'regis':
                try:
                    nombre, email, contraseña, rol = payload.split('|')
                    cursor.execute('INSERT INTO usuarios (nombre, email, contraseña, rol) VALUES (?, ?, ?, ?)', 
                                   (nombre, email, contraseña, rol))
                    user_id = cursor.lastrowid
                    conn.commit()
                    response = f'OK|{user_id}'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'login':
                try:
                    email, contraseña = payload.split('|')
                    cursor.execute('SELECT id_usuario FROM usuarios WHERE email=? AND contraseña=?', (email, contraseña))
                    user = cursor.fetchone()
                    if user:
                        response = f'OK|{user[0]}'
                    else:
                        response = 'ERR|Credenciales inválidas'
                except Exception as e:
                    response = f'ERR|{str(e)}'
            elif comando == 'cpass':
                try:
                    id_usuario, nueva_contraseña = payload.split('|')
                    cursor.execute('UPDATE usuarios SET contraseña = ? WHERE id_usuario = ?', (nueva_contraseña, id_usuario))
                    conn.commit()
                    response = 'OK|Contraseña actualizada'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
            elif comando == 'cname':
                try:
                    id_usuario, nuevo_nombre = payload.split('|')
                    cursor.execute('UPDATE usuarios SET nombre = ? WHERE id_usuario = ?', (nuevo_nombre, id_usuario))
                    conn.commit()
                    response = 'OK|Nombre actualizado'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
            elif comando == 'cmail':
                try:
                    id_usuario, nuevo_email = payload.split('|')
                    cursor.execute('UPDATE usuarios SET email = ? WHERE id_usuario = ?', (nuevo_email, id_usuario))
                    conn.commit()
                    response = 'OK|Email actualizado'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
            elif comando == 'delac':
                try:
                    id_usuario = payload
                    cursor.execute('DELETE FROM usuarios WHERE id_usuario = ?', (id_usuario,))
                    conn.commit()
                    response = 'OK|Cuenta eliminada'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'ginfo':
                try:
                    id_usuario = payload
                    cursor.execute('SELECT id_usuario, nombre, email, rol, fecha_creacion FROM usuarios WHERE id_usuario = ?', (id_usuario,))
                    user = cursor.fetchone()
                    if user:
                        user_str = f'{user[0]}|{user[1]}|{user[2]}|{user[3]}|{user[4]}'
                        response = f'OK|{user_str}'
                    else:
                        response = 'ERR|Usuario no encontrado'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
            else:
                response = 'ERR|Comando no reconocido'

            response_message = f'{len(response):05}{service}{response}'.encode()
            sock.sendall(response_message)
            print('Respuesta enviada:', response_message)






finally:
    print('closing socket')
    sock.close()
    conn.close()