import socket
import sqlite3
import os
import re
import tempfile
import shutil
import os, re, tempfile, shutil, sqlite3, base64, mimetypes

#TODO HACER DOWNLOAD




sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bus_addr = ('localhost', 5000)
sock.connect(bus_addr)


STORAGE_ROOT = os.path.join(os.getcwd(), "storage")  # cambia si quieres otra ruta base
MAX_WIRE_BYTES = 99_999


def _safe_filename(name: str) -> str:
    # quita directorios, caracteres raros y normaliza espacios
    base = os.path.basename(name).strip()
    # opcional: limitar charset (evita controles/pipes)
    base = re.sub(r'[\\/:*?"<>|\r\n\t]+', '_', base)
    return base or "archivo"

def _resolve_collision(dest_dir: str, filename: str) -> str:
    name, ext = os.path.splitext(filename)
    candidate = filename
    i = 1
    while os.path.exists(os.path.join(dest_dir, candidate)):
        candidate = f"{name}({i}){ext}"
        i += 1
    return candidate

import socket
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
            comando = data[5:10].decode()
            payload = data[10:].decode()

            if comando == 'mkdir':
                try:
                    nombre, propietario, carpeta_padre = payload.split('|')
                    # Normalizar carpeta padre
                    carpeta_padre = carpeta_padre.strip()
                    carpeta_val = carpeta_padre if carpeta_padre not in ('', 'None') else None

                    # Ejecutar INSERT a través del servicio sbase
                    sql = 'INSERT INTO carpeta (nombre, propietario, carpeta_padre) VALUES (?, ?, ?)'
                    params = (nombre.strip(), propietario.strip(), carpeta_val)

                    # Llamamos al servicio de base de datos en lugar de usar cursor directamente
                    result = db_query(sock, sql, params, service='sbase')

                    response = 'OK|Carpeta creada' if not str(result).startswith('ERR|') else result
                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'rmdir':
                # payload: "propietario|carpeta_ref" (carpeta_ref puede ser ID o nombre)
                try:
                    propietario, carpeta_ref = payload.split('|', 1)
                    propietario = propietario.strip()
                    ref = (carpeta_ref or '').strip()

                    if not propietario or not ref:
                        response = 'ERR|Propietario o carpeta_ref vacío'
                    else:
                        # 1) Resolver id de carpeta garantizando pertenencia
                        if ref.isdigit():
                            rows = db_query(sock, 
                                            "SELECT id_carpeta FROM carpeta WHERE id_carpeta = ? AND propietario = ?",
                                            [int(ref), propietario],
                                            service='sbase')
                        else:
                            # Con UNIQUE(nombre, propietario) esto no es ambiguo
                            rows = db_query(sock, 
                                            "SELECT id_carpeta FROM carpeta WHERE nombre = ? AND propietario = ?",
                                            [ref, propietario],
                                            service='sbase')

                        # db_query devuelve lista de tuplas en SELECT
                        if not rows:
                            response = 'ERR|Carpeta no encontrada para el propietario'
                        elif len(rows) > 1:
                            # Solo por si cambias la unicidad en el futuro
                            response = 'ERR|Carpeta ambigua (múltiples coincidencias). Usa ID.'
                        else:
                            carpeta_id = rows[0][0]

                            # 2) Borrado recursivo (ON DELETE CASCADE se encarga del contenido)
                            res = db_query(sock, 
                                        "DELETE FROM carpeta WHERE id_carpeta = ? AND propietario = ?",
                                        [carpeta_id, propietario],
                                        service='sbase')
                            # res típico: "1 filas afectadas"
                            try:
                                affected = int(str(res).split()[0])
                            except Exception:
                                affected = 0

                            if affected == 0:
                                response = 'ERR|No se eliminó ninguna carpeta'
                            else:
                                response = 'OK|Carpeta y contenido eliminados (recursivo)'

                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'lsall':
                try:
                    # --- validar payload ---
                    if '|' not in payload:
                        response = 'ERR|Payload inválido. Formato: propietario|carpeta_ref'
                    else:
                        propietario, carpeta_ref = payload.split('|', 1)
                        propietario = (propietario or '').strip()
                        ref = (carpeta_ref or '').strip()

                        if not propietario:
                            response = 'ERR|Propietario vacío'
                        else:
                            response = ''  # asegurar string

                            # 1) Resolver folder_id (None = raíz)
                            folder_id = None
                            if ref and ref.lower() != 'root':
                                if ref.isdigit():
                                    # validar pertenencia por ID
                                    rows = db_query(
                                        sock,
                                        'SELECT id_carpeta FROM carpeta WHERE id_carpeta = ? AND propietario = ?',
                                        [int(ref), propietario],
                                        service='sbase'
                                    )
                                else:
                                    # resolver por nombre (podría ser ambiguo si cambias unicidad por nivel)
                                    rows = db_query(
                                        sock,
                                        'SELECT id_carpeta FROM carpeta WHERE propietario = ? AND nombre = ?',
                                        [propietario, ref],
                                        service='sbase'
                                    )

                                if not rows:
                                    response = 'ERR|Carpeta no encontrada'
                                elif len(rows) > 1:
                                    response = 'ERR|Carpeta ambigua (varias con el mismo nombre). Usa ID.'
                                else:
                                    folder_id = rows[0][0]

                            if response and response.startswith('ERR|'):
                                pass
                            else:
                                # 2) Listar carpetas hijas directas
                                if folder_id is None:
                                    rows_folders = db_query(
                                        sock,
                                        'SELECT id_carpeta, nombre, propietario, carpeta_padre '
                                        'FROM carpeta WHERE propietario = ? AND carpeta_padre IS NULL',
                                        [propietario],
                                        service='sbase'
                                    )
                                else:
                                    rows_folders = db_query(
                                        sock,
                                        'SELECT id_carpeta, nombre, propietario, carpeta_padre '
                                        'FROM carpeta WHERE propietario = ? AND carpeta_padre = ?',
                                        [propietario, folder_id],
                                        service='sbase'
                                    )

                                carpetas_str = ''
                                if rows_folders:
                                    carpetas_str = '|'.join(
                                        f'{c[0]},{c[1]},{c[2]},{c[3]}'
                                        for c in rows_folders
                                    )

                                # 3) Listar archivos directos
                                if folder_id is None:
                                    rows_files = db_query(
                                        sock,
                                        'SELECT id_archivo, nombre, tipo, tamaño, fecha_subida, propietario, visibilidad, carpeta, ruta '
                                        'FROM archivo WHERE propietario = ? AND carpeta IS NULL',
                                        [propietario],
                                        service='sbase'
                                    )
                                else:
                                    rows_files = db_query(
                                        sock,
                                        'SELECT id_archivo, nombre, tipo, tamaño, fecha_subida, propietario, visibilidad, carpeta, ruta '
                                        'FROM archivo WHERE propietario = ? AND carpeta = ?',
                                        [propietario, folder_id],
                                        service='sbase'
                                    )

                                archivos_str = ''
                                if rows_files:
                                    archivos_str = '|'.join(
                                        f'{a[0]},{a[1]},{a[2]},{a[3]},{a[4]},{a[5]},{a[6]},{a[7]},{a[8]}'
                                        for a in rows_files
                                    )

                                # 4) Respuesta unificada
                                response = f'OK|FOLDERS:{carpetas_str}|FILES:{archivos_str}'

                except Exception as e:
                    # envía el texto del error para que lo puedas ver arriba en el cliente
                    response = f'ERR|{str(e)}'

            elif comando == 'rmfil':
                # payload: "propietario|archivo_ref" (archivo_ref puede ser ID o nombre)
                try:
                    propietario, archivo_ref = payload.split('|', 1)
                    propietario = propietario.strip()
                    ref = (archivo_ref or '').strip()

                    if not propietario or not ref:
                        response = 'ERR|Propietario o referencia de archivo vacío'
                    else:
                        # Resolver archivo garantizando pertenencia (ID o nombre)
                        if ref.isdigit():
                            rows = db_query(
                                sock,
                                'SELECT id_archivo, ruta FROM archivo WHERE id_archivo = ? AND propietario = ?',
                                [int(ref), propietario],
                                service='sbase'
                            )
                        else:
                            rows = db_query(
                                sock,
                                'SELECT id_archivo, ruta FROM archivo WHERE nombre = ? AND propietario = ?',
                                [ref, propietario],
                                service='sbase'
                            )

                        if not rows:
                            response = 'ERR|Archivo no encontrado para el propietario'
                        elif len(rows) > 1:
                            # Por si en el futuro usas UNIQUE(nombre, propietario, carpeta)
                            response = 'ERR|Nombre ambiguo (múltiples coincidencias). Usa ID o especifique carpeta.'
                        else:
                            archivo_id, ruta = rows[0]

                            # Borrar registro en BDD
                            res = db_query(
                                sock,
                                'DELETE FROM archivo WHERE id_archivo = ? AND propietario = ?',
                                [archivo_id, propietario],
                                service='sbase'
                            )
                            try:
                                affected = int(str(res).split()[0])
                            except Exception:
                                affected = 0

                            if affected == 0:
                                response = 'ERR|No se eliminó ningun archivo (no encontrado o sin permiso)'
                            else:
                                # Intentar eliminar el fichero en disco (no falla si no se puede borrar)
                                try:
                                    if ruta and os.path.exists(ruta):
                                        os.remove(ruta)
                                    response = 'OK|Archivo eliminado'
                                except Exception as e:
                                    response = f'OK|Registro eliminado, fallo al borrar fichero en disco: {e}'

                except Exception as e:
                    response = f'ERR|{str(e)}'
         
            elif comando == 'upfil':
                try:
                    # Espera todo en TEXTO por el bus:
                    # "nombre|tipo|tamaño|propietario|visibilidad|carpeta|<BASE64>"
                    response = ''
                    if not isinstance(payload, str):
                        response = 'ERR|Payload debe ser str (usa Base64 en el cliente)'
                    else:
                        parts = payload.split('|', 6)
                        if len(parts) != 7:
                            response = 'ERR|Payload incompleto (se esperaban 6 separadores | y luego el base64)'
                        else:
                            nombre, tipo, tam_s, propietario, visibilidad, carpeta_str, contenido_b64 = [p.strip() for p in parts]

                            if not nombre or not propietario:
                                response = 'ERR|Nombre y propietario son obligatorios'
                            else:
                                # Decodificar Base64 a bytes
                                try:
                                    contenido = base64.b64decode(contenido_b64, validate=True)
                                except Exception as e:
                                    response = f'ERR|Base64 inválido: {e}'
                                else:
                                    real_size = len(contenido)
                                    if tam_s and tam_s.isdigit() and int(tam_s) != real_size:
                                        response = f'ERR|Tamaño declarado ({tam_s}) no coincide con recibido ({real_size})'
                                    else:
                                        # --- Resolver carpeta destino en DB (por nombre del propietario) ---
                                        # "" o "root" => subir a raíz (carpeta = NULL)
                                        carpeta_id = None
                                        ref = carpeta_str.strip()
                                        if ref and ref.lower() != 'root':
                                            rows = db_query(
                                                sock,
                                                'SELECT id_carpeta FROM carpeta WHERE nombre = ? AND propietario = ?',
                                                [ref, propietario],
                                                service='sbase'
                                            )
                                            if not rows:
                                                response = 'ERR|Carpeta no existe para el propietario'
                                            elif len(rows) > 1:
                                                response = 'ERR|Carpeta ambigua (varias con ese nombre). Use ID.'
                                            else:
                                                carpeta_id = rows[0][0]

                                        if response and response.startswith('ERR|'):
                                            pass
                                        else:
                                            # --- Guardado en disco ---
                                            subdir = ref if (ref and ref.lower() != 'root') else 'root'
                                            dest_dir = os.path.join(STORAGE_ROOT, str(propietario), str(subdir))
                                            os.makedirs(dest_dir, exist_ok=True)

                                            filename = _resolve_collision(dest_dir, _safe_filename(nombre))
                                            dest_path = os.path.join(dest_dir, filename)

                                            tmp_path = None
                                            try:
                                                with tempfile.NamedTemporaryFile(dir=dest_dir, delete=False) as tmp:
                                                    tmp.write(contenido)
                                                    tmp_path = tmp.name
                                                shutil.move(tmp_path, dest_path)
                                                tmp_path = None
                                            finally:
                                                if tmp_path and os.path.exists(tmp_path):
                                                    try:
                                                        os.remove(tmp_path)
                                                    except Exception:
                                                        pass

                                            # --- Insert metadata en DB vía sbase ---
                                            try:
                                                db_query(
                                                    sock,
                                                    'INSERT INTO archivo (nombre, tipo, tamaño, propietario, visibilidad, carpeta, ruta) '
                                                    'VALUES (?, ?, ?, ?, ?, ?, ?)',
                                                    [filename, (tipo or 'application/octet-stream'), real_size,
                                                    propietario, (visibilidad or 'private'), carpeta_id, dest_path],
                                                    service='sbase'
                                                )
                                                response = f'OK|Archivo subido|ruta={dest_path}'
                                            except Exception as e:
                                                # Si falla el INSERT, borramos el archivo físico para no dejar basura
                                                try:
                                                    if os.path.exists(dest_path):
                                                        os.remove(dest_path)
                                                except Exception:
                                                    pass
                                                response = f'ERR|{str(e)}'

                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'dwfil':
                try:
                    # payload: "propietario|archivo_ref"
                    parts = payload.split('|', 1)
                    if len(parts) != 2:
                        response = 'ERR|Payload inválido. Formato: propietario|archivo_ref'
                    else:
                        propietario, archivo_ref = [p.strip() for p in parts]
                        if not propietario or not archivo_ref:
                            response = 'ERR|Propietario o referencia vacío'
                        else:
                            # Normaliza propietario si en DB es INTEGER
                            try:
                                propietario_db = int(propietario)
                            except ValueError:
                                propietario_db = propietario  # si tu esquema guarda TEXT

                            # Resolver archivo (ID o nombre) garantizando pertenencia
                            if archivo_ref.isdigit():
                                rows = db_query(
                                    sock,
                                    'SELECT id_archivo, nombre, tipo, tamaño, fecha_subida, propietario, visibilidad, carpeta, ruta '
                                    'FROM archivo WHERE id_archivo = ? AND propietario = ?',
                                    [int(archivo_ref), propietario_db],
                                    service='sbase'
                                )
                            else:
                                rows = db_query(
                                    sock,
                                    'SELECT id_archivo, nombre, tipo, tamaño, fecha_subida, propietario, visibilidad, carpeta, ruta '
                                    'FROM archivo WHERE nombre = ? AND propietario = ?',
                                    [archivo_ref, propietario_db],
                                    service='sbase'
                                )

                            if not rows:
                                response = 'ERR|Archivo no encontrado para el propietario'
                            elif len(rows) > 1:
                                # Por si en el futuro permites mismo nombre en varias carpetas
                                response = 'ERR|Nombre ambiguo (múltiples coincidencias). Usa ID.'
                            else:
                                (id_archivo, nombre, tipo_db, tam_db, fecha_subida,
                                propietario_row, visibilidad, carpeta, ruta) = rows[0]

                                if not ruta or not os.path.exists(ruta):
                                    response = 'ERR|Ruta de archivo inexistente en disco'
                                else:
                                    # Leer y codificar Base64
                                    with open(ruta, 'rb') as f:
                                        data = f.read()
                                    b64 = base64.b64encode(data).decode('ascii')

                                    # MIME (fallback por nombre)
                                    mime = tipo_db or (mimetypes.guess_type(nombre)[0] or 'application/octet-stream')
                                    size_real = len(data)

                                    # Construir respuesta textual
                                    body = f"OK|NAME:{nombre}|TYPE:{mime}|SIZE:{size_real}|DATE:{fecha_subida}|B64:{b64}"

                                    # Verificar límite del cable (aprox; suma +15 por opcode)
                                    if len(body.encode('utf-8')) + 15 > MAX_WIRE_BYTES:
                                        response = 'ERR|Archivo demasiado grande para una sola respuesta. Usa descarga por chunks.'
                                    else:
                                        response = body

                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'renam':
                # payload:
                #   1) "nombre_actual|nuevo_nombre|propietario"
                #   2) "tipo|nombre_actual|nuevo_nombre|propietario"   (tipo: file/folder o f/d)
                try:
                    response = ''
                    parts = [p.strip() for p in payload.split('|')]

                    if len(parts) == 3:
                        tipo = ''
                        nombre_actual, nuevo_nombre, propietario = parts
                    elif len(parts) == 4:
                        nombre_actual, nuevo_nombre, propietario, tipo = parts
                        tipo = tipo.lower()
                        if   tipo in ('f', 'file'):   tipo = 'file'
                        elif tipo in ('d', 'folder'): tipo = 'folder'
                        else:
                            response = 'ERR|Tipo inválido (usa file/folder)'
                    else:
                        response = 'ERR|Payload inválido. Usa: nombre|nuevo|propietario  o  tipo|nombre|nuevo|propietario'

                    if not response:
                        if not nombre_actual or not nuevo_nombre or not propietario:
                            response = 'ERR|Nombre actual, nuevo nombre y propietario son obligatorios'
                        elif nombre_actual == nuevo_nombre:
                            response = 'OK|Sin cambios (el nombre es el mismo)'

                    # Autodetección del tipo si no vino
                    if not response and not tipo:
                        file_rows = db_query(
                            sock,
                            'SELECT id_archivo FROM archivo WHERE nombre = ? AND propietario = ? LIMIT 2',
                            [nombre_actual, propietario],
                            service='sbase'
                        )
                        folder_rows = db_query(
                            sock,
                            'SELECT id_carpeta FROM carpeta WHERE nombre = ? AND propietario = ? LIMIT 2',
                            [nombre_actual, propietario],
                            service='sbase'
                        )
                        total = (1 if file_rows else 0) + (1 if folder_rows else 0)
                        if total == 0:
                            response = 'ERR|No existe archivo ni carpeta con ese nombre para el propietario'
                        elif total > 1:
                            response = 'ERR|Nombre ambigua (existe archivo y carpeta). Especifica tipo (file/folder).'
                        else:
                            tipo = 'file' if file_rows else 'folder'

                    # Renombrar según tipo
                    if not response and tipo == 'file':
                        # Colisión con UNIQUE(nombre, propietario) en archivo
                        clash = db_query(
                            sock,
                            'SELECT 1 FROM archivo WHERE nombre = ? AND propietario = ?',
                            [nuevo_nombre, propietario],
                            service='sbase'
                        )
                        if clash:
                            response = 'ERR|Ya existe un archivo con ese nombre para el propietario'
                        else:
                            res = db_query(
                                sock,
                                'UPDATE archivo SET nombre = ? WHERE nombre = ? AND propietario = ?',
                                [nuevo_nombre, nombre_actual, propietario],
                                service='sbase'
                            )
                            try:
                                affected = int(str(res).split()[0])
                            except Exception:
                                affected = 0
                            response = 'OK|Archivo renombrado' if affected > 0 else 'ERR|Archivo no encontrado o no pertenece al propietario'

                    elif not response and tipo == 'folder':
                        # Colisión con UNIQUE(nombre, propietario) en carpeta
                        clash = db_query(
                            sock,
                            'SELECT 1 FROM carpeta WHERE nombre = ? AND propietario = ?',
                            [nuevo_nombre, propietario],
                            service='sbase'
                        )
                        if clash:
                            response = 'ERR|Ya existe una carpeta con ese nombre para el propietario'
                        else:
                            res = db_query(
                                sock,
                                'UPDATE carpeta SET nombre = ? WHERE nombre = ? AND propietario = ?',
                                [nuevo_nombre, nombre_actual, propietario],
                                service='sbase'
                            )
                            try:
                                affected = int(str(res).split()[0])
                            except Exception:
                                affected = 0
                            response = 'OK|Carpeta renombrada' if affected > 0 else 'ERR|Carpeta no encontrada o no pertenece al propietario'

                    if not response:
                        response = 'ERR|No se pudo determinar el tipo a renombrar'

                except Exception as e:
                    response = f'ERR|{str(e)}'

            elif comando == 'movef':
                # payload: "propietario|archivo_ref|carpeta_nueva_ref"
                try:
                    parts = payload.split('|')
                    if len(parts) != 3:
                        response = 'ERR|Payload inválido. Formato: propietario|archivo_ref|carpeta_nueva_ref'
                    else:
                        propietario, archivo_ref, carpeta_ref = [p.strip() for p in parts]
                        if not propietario or not archivo_ref:
                            response = 'ERR|Propietario y archivo_ref son obligatorios'
                        else:
                            # --- Resolver archivo (ID o nombre) garantizando pertenencia ---
                            if archivo_ref.isdigit():
                                rows_file = db_query(
                                    sock,
                                    'SELECT id_archivo FROM archivo WHERE id_archivo = ? AND propietario = ?',
                                    [int(archivo_ref), propietario],
                                    service='sbase'
                                )
                            else:
                                rows_file = db_query(
                                    sock,
                                    'SELECT id_archivo FROM archivo WHERE nombre = ? AND propietario = ?',
                                    [archivo_ref, propietario],
                                    service='sbase'
                                )

                            if not rows_file:
                                response = 'ERR|Archivo no encontrado para el propietario'
                            elif len(rows_file) > 1:
                                response = 'ERR|Archivo ambiguo (múltiples coincidencias). Usa ID o especifica carpeta origen.'
                            else:
                                archivo_id = rows_file[0][0]

                                # --- Resolver carpeta destino ---
                                # '' o 'root' => mover a raíz (NULL)
                                if carpeta_ref == '' or carpeta_ref.lower() == 'root':
                                    carpeta_dest_id = None
                                else:
                                    if carpeta_ref.isdigit():
                                        rows_c = db_query(
                                            sock,
                                            'SELECT id_carpeta FROM carpeta WHERE id_carpeta = ? AND propietario = ?',
                                            [int(carpeta_ref), propietario],
                                            service='sbase'
                                        )
                                    else:
                                        rows_c = db_query(
                                            sock,
                                            'SELECT id_carpeta FROM carpeta WHERE nombre = ? AND propietario = ?',
                                            [carpeta_ref, propietario],
                                            service='sbase'
                                        )

                                    if not rows_c:
                                        response = 'ERR|Carpeta destino no encontrada para el propietario'
                                    elif len(rows_c) > 1:
                                        response = 'ERR|Carpeta destino ambigua (múltiples coincidencias). Usa ID.'
                                    else:
                                        carpeta_dest_id = rows_c[0][0]

                                if not ('response' in locals() and response.startswith('ERR|')):
                                    # --- Ejecutar movimiento ---
                                    if carpeta_dest_id is None:
                                        res = db_query(
                                            sock,
                                            'UPDATE archivo SET carpeta = NULL WHERE id_archivo = ? AND propietario = ?',
                                            [archivo_id, propietario],
                                            service='sbase'
                                        )
                                    else:
                                        res = db_query(
                                            sock,
                                            'UPDATE archivo SET carpeta = ? WHERE id_archivo = ? AND propietario = ?',
                                            [carpeta_dest_id, archivo_id, propietario],
                                            service='sbase'
                                        )

                                    try:
                                        affected = int(str(res).split()[0])
                                    except Exception:
                                        affected = 0

                                    if affected == 0:
                                        response = 'ERR|No se pudo mover (archivo no encontrado o sin permiso)'
                                    else:
                                        destino_txt = 'root' if carpeta_dest_id is None else str(carpeta_dest_id)
                                        response = f'OK|Archivo movido a {destino_txt}'

                except Exception as e:
                    response = f'ERR|{str(e)}'

            else:
                response = 'ERR|Comando no reconocido'

            response_message = f'{len(response):05}{service}{response}'.encode()
            sock.sendall(response_message)
            print('Respuesta enviada:', response_message)


finally:
    sock.close()


