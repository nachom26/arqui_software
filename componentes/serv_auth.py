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
            comando = data[5:15].decode()
            payload = data[15:].decode()

            if comando == 'createuser':
                try:
                    nombre, email, contraseña, rol = payload.split('|')
                    cursor.execute('INSERT INTO usuarios (nombre, email, contraseña, rol) VALUES (?, ?, ?, ?)', 
                                   (nombre, email, contraseña, rol))
                    conn.commit()
                    response = 'OK|Usuario creado'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'loginusers':
                try:
                    nombre, contraseña = payload.split('|')
                    cursor.execute('SELECT * FROM usuarios WHERE nombre=? AND contraseña=?', (nombre, contraseña))
                    user = cursor.fetchone()
                    if user:
                        response = 'OK|Login exitoso'
                    else:
                        response = 'ERR|Credenciales inválidas'
                except Exception as e:
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