import socket
import sqlite3

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

bus_addr = ('localhost', 5000)
sock.connect(bus_addr)


import ast

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket cerrado mientras se recibía la respuesta")
        buf += chunk
    return buf

def send_bus(sock: socket.socket, service: str, command: str, payload: str) -> bytes:
    """
    Protocolo:
      [LEN 5 ascii] + [SERVICE ascii] + [COMMAND 5 bytes] + [PAYLOAD utf-8]
    Respuesta:
      [LEN 5 ascii] + [SERVICE ascii] + <contenido>

    - command: EXACTAMENTE 5 bytes (se trunca o rellena con espacios).
    - payload: str (el bus es sólo texto).
    """
    svc = service.encode('ascii', 'ignore')
    cmd = command.encode('ascii', 'ignore')[:5].ljust(5, b' ')
    body = svc + cmd + payload.encode('utf-8')
    header = f"{len(body):05}".encode('ascii')

    sock.sendall(header + body)

    # respuesta
    resp_len = int(_recv_exact(sock, 5).decode('ascii'))
    data = _recv_exact(sock, resp_len)
    # El servicio siempre antepone SERVICE en la respuesta
    if data.startswith(svc):
        return data[len(svc):]
    return data


import ast

def db_query(sock, sql: str, params=None, service: str = 'sbase'):
    # payload: "<sql>|<repr(params)>"
    payload = f"{sql}|{repr(list(params))}" if params else f"{sql}|"

    raw = send_bus(sock, service, 'query', payload)  # bytes sin SERVICE (send_bus ya lo quita)
    text = raw.decode('utf-8', 'replace').strip()

    print(text)

    # Si el servicio devuelve "sbaseERR|..." y no lo limpiaste, límpialo aquí también:
    if ('ERR|' in text ):
        # cubre "ERR|..." y "sbaseERR|..."
        # extrae la parte desde "ERR|" por si viene con prefijos
        err_idx = text.find('ERR|')
        raise RuntimeError(text[err_idx:])

    # Normalizar prefijos "OK" / "OK|"
    if text.startswith('OK'):
        t = text[2:]
        if t.startswith('|'):
            t = t[1:]
        text = t.strip()

    # SELECT -> parsea lista/tuplas
    if sql.lstrip().upper().startswith('SELECT'):
        if text == '' or text == 'OK':
            return []
        try:
            return ast.literal_eval(text)  # '[(1,)]' -> [(1,)]
        except Exception:
            return []  # fallback seguro
    else:
        # no-SELECT -> string, p.ej. "1 filas afectadas"
        return text



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
                    # payload: "nombre|email|contraseña|rol"
                    parts = payload.split('|', 3)
                    if len(parts) != 4:
                        response = 'ERR|Payload inválido. Formato: nombre|email|contraseña|rol'
                    else:
                        nombre, email, contraseña, rol = [p.strip() for p in parts]

                        if not nombre or not email or not contraseña:
                            response = 'ERR|Nombre, email y contraseña son obligatorios'
                        else:
                            rol = (rol or 'usuario').strip().lower()

                            # 1) INSERT vía sbase
                            try:
                                _ = db_query(
                                    sock,
                                    'INSERT INTO usuarios (nombre, email, contraseña, rol) VALUES (?, ?, ?, ?)',
                                    [nombre, email, contraseña, rol],
                                    service='sbase'
                                )
                            except Exception as e:
                                response = f'ERR|{str(e)}'
                            else:
                                # 2) Recuperar el id de esa MISMA conexión
                                try:
                                    rows = db_query(
                                        sock,
                                        'SELECT last_insert_rowid()',
                                        [],
                                        service='sbase'
                                    )
                                    if rows and len(rows[0]) >= 1:
                                        user_id = rows[0][0]
                                        # Ahora devolvemos también el rol
                                        response = f'OK|{user_id}|{rol}'
                                    else:
                                        response = 'ERR|No se pudo recuperar el id (LAST_INSERT_ROWID vacío)'
                                except Exception as e:
                                    response = f'ERR|No se pudo recuperar el id: {e}'
                except Exception as e:
                    response = f'ERR|{str(e)}'




            elif comando == 'login':
                try:
                    # payload: "email|contraseña"
                    parts = payload.split('|', 1)
                    if len(parts) != 2:
                        response = 'ERR|Payload inválido. Formato: email|contraseña'
                    else:
                        email, contraseña = [p.strip() for p in parts]
                        if not email or not contraseña:
                            response = 'ERR|Email y contraseña son obligatorios'
                        else:
                            # Consulta vía servicio sbase: buscamos id y rol
                            rows = db_query(
                                sock,
                                'SELECT id_usuario, rol FROM usuarios WHERE email = ? AND contraseña = ?',
                                [email, contraseña],
                                service='sbase'
                            )

                            if rows:
                                user_id, rol = rows[0]
                                response = f'OK|{user_id}|{rol}'
                                # Registrar en historial (best effort)
                                try:
                                    db_query(
                                        sock,
                                        'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
                                        ['login_ok', str(user_id), 'usuarios'],
                                        service='sbase'
                                    )
                                except Exception:
                                    pass
                            else:
                                response = 'ERR|Credenciales inválidas'
                                # Registrar intento fallido (best effort)
                                try:
                                    db_query(
                                        sock,
                                        'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
                                        ['login_fail', email, 'usuarios'],
                                        service='sbase'
                                    )
                                except Exception:
                                    pass

                except Exception as e:
                    response = f'ERR|{str(e)}'


            elif comando == 'cpass':
                # payload: "id_usuario|nueva_contraseña"
                try:
                    parts = payload.split('|', 1)
                    if len(parts) != 2:
                        response = 'ERR|Payload inválido. Formato: id_usuario|nueva_contraseña'
                    else:
                        id_usuario, nueva_contraseña = [p.strip() for p in parts]
                        if not id_usuario or not nueva_contraseña:
                            response = 'ERR|ID y nueva contraseña son obligatorios'
                        else:
                            res = db_query(sock,
                                        'UPDATE usuarios SET contraseña = ? WHERE id_usuario = ?',
                                        [nueva_contraseña, id_usuario],
                                        service='sbase')
                            try:
                                affected = int(str(res).split()[0])
                            except Exception:
                                affected = 0

                            if affected == 0:
                                response = 'ERR|Usuario no encontrado'
                            else:
                                response = 'OK|Contraseña actualizada'
                                # log (best-effort)
                                try:
                                    db_query(sock, 'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
                                            ['change_password', str(id_usuario), 'usuarios'],
                                            service='sbase')
                                except Exception:
                                    pass
                except Exception as e:
                    response = f'ERR|{str(e)}'


            elif comando == 'cname':
                # payload: "id_usuario|nuevo_nombre"
                try:
                    parts = payload.split('|', 1)
                    if len(parts) != 2:
                        response = 'ERR|Payload inválido. Formato: id_usuario|nuevo_nombre'
                    else:
                        id_usuario, nuevo_nombre = [p.strip() for p in parts]
                        if not id_usuario or not nuevo_nombre:
                            response = 'ERR|ID y nuevo nombre son obligatorios'
                        else:
                            try:
                                res = db_query(sock,
                                            'UPDATE usuarios SET nombre = ? WHERE id_usuario = ?',
                                            [nuevo_nombre, id_usuario],
                                            service='sbase')
                            except Exception as e:
                                # devolver tal cual (p.ej., UNIQUE(nombre) violado)
                                response = f'ERR|{str(e)}'
                            else:
                                try:
                                    affected = int(str(res).split()[0])
                                except Exception:
                                    affected = 0
                                response = 'OK|Nombre actualizado' if affected > 0 else 'ERR|Usuario no encontrado'
                                # log
                                if affected > 0:
                                    try:
                                        db_query(sock, 'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
                                                ['change_name', str(id_usuario), 'usuarios'],
                                                service='sbase')
                                    except Exception:
                                        pass
                except Exception as e:
                    response = f'ERR|{str(e)}'


            elif comando == 'cmail':
                # payload: "id_usuario|nuevo_email"
                try:
                    parts = payload.split('|', 1)
                    if len(parts) != 2:
                        response = 'ERR|Payload inválido. Formato: id_usuario|nuevo_email'
                    else:
                        id_usuario, nuevo_email = [p.strip() for p in parts]
                        if not id_usuario or not nuevo_email:
                            response = 'ERR|ID y nuevo email son obligatorios'
                        else:
                            try:
                                res = db_query(sock,
                                            'UPDATE usuarios SET email = ? WHERE id_usuario = ?',
                                            [nuevo_email, id_usuario],
                                            service='sbase')
                            except Exception as e:
                                # p.ej., UNIQUE(email) violado
                                response = f'ERR|{str(e)}'
                            else:
                                try:
                                    affected = int(str(res).split()[0])
                                except Exception:
                                    affected = 0
                                response = 'OK|Email actualizado' if affected > 0 else 'ERR|Usuario no encontrado'
                                # log
                                if affected > 0:
                                    try:
                                        db_query(sock, 'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
                                                ['change_email', str(id_usuario), 'usuarios'],
                                                service='sbase')
                                    except Exception:
                                        pass
                except Exception as e:
                    response = f'ERR|{str(e)}'


            elif comando == 'delac':
                # payload: "id_usuario"
                try:
                    id_usuario = payload.strip()
                    if not id_usuario:
                        response = 'ERR|ID de usuario obligatorio'
                    else:
                        # (opcional) borrar primero dependencias si tu schema no las maneja en cascada
                        res = db_query(sock,
                                    'DELETE FROM usuarios WHERE id_usuario = ?',
                                    [id_usuario],
                                    service='sbase')
                        try:
                            affected = int(str(res).split()[0])
                        except Exception:
                            affected = 0

                        if affected == 0:
                            response = 'ERR|Usuario no encontrado'
                        else:
                            response = 'OK|Cuenta eliminada'
                            # log
                            try:
                                db_query(sock, 'INSERT INTO historial (accion, usuario, entidad_afectada) VALUES (?, ?, ?)',
                                        ['delete_account', str(id_usuario), 'usuarios'],
                                        service='sbase')
                            except Exception:
                                pass
                except Exception as e:
                    response = f'ERR|{str(e)}'


            elif comando == 'ginfo':
                # payload: "id_usuario"
                try:
                    id_usuario = payload.strip()
                    if not id_usuario:
                        response = 'ERR|ID de usuario obligatorio'
                    else:
                        rows = db_query(sock,
                                        'SELECT id_usuario, nombre, email, rol, fecha_creacion FROM usuarios WHERE id_usuario = ?',
                                        [id_usuario],
                                        service='sbase')
                        if rows:
                            u = rows[0]
                            # Formato: OK|<id>|<nombre>|<email>|<rol>|<fecha>
                            response = f'OK|{u[0]}|{u[1]}|{u[2]}|{u[3]}|{u[4]}'
                        else:
                            response = 'ERR|Usuario no encontrado'
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
