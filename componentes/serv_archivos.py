import socket
import sqlite3
import os
import re
import tempfile
import shutil
import os, re, tempfile, shutil, sqlite3, base64

#TODO HACER DOWNLOAD




sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bus_addr = ('localhost', 5000)
sock.connect(bus_addr)
conn = sqlite3.connect('archivador.db')
cursor = conn.cursor()

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

STORAGE_ROOT = os.path.join(os.getcwd(), "storage")  # cambia si quieres otra ruta base

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
                    cursor.execute('INSERT INTO carpeta (nombre, propietario, carpeta_padre) VALUES (?, ?, ?)', 
                                   (nombre, propietario, carpeta_padre if carpeta_padre != 'None' and carpeta_padre != '' else None))
                    conn.commit()
                    response = 'OK|Carpeta creada'
                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
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
                        # Resolver folder_id garantizando pertenencia
                        if ref.isdigit():
                            cursor.execute(
                                'SELECT id_carpeta FROM carpeta WHERE id_carpeta = ? AND propietario = ?',
                                (int(ref), propietario)
                            )
                        else:
                            # Si en `carpeta` tienes UNIQUE(nombre, propietario),
                            # esto es no ambiguo dentro del propietario.
                            cursor.execute(
                                'SELECT id_carpeta FROM carpeta WHERE nombre = ? AND propietario = ?',
                                (ref, propietario)
                            )

                        row = cursor.fetchone()
                        if not row:
                            response = 'ERR|Carpeta no encontrada para el propietario'
                        else:
                            carpeta_id = row[0]

                            # Borrado recursivo trivial gracias a ON DELETE CASCADE
                            cursor.execute('DELETE FROM carpeta WHERE id_carpeta = ? AND propietario = ?',
                                        (carpeta_id, propietario))
                            if cursor.rowcount == 0:
                                response = 'ERR|No se eliminó ninguna carpeta'
                            else:
                                conn.commit()
                                response = 'OK|Carpeta y contenido eliminados (recursivo)'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'



            elif comando == 'lsall':
                try:
                    response = ''
                    propietario, carpeta_ref = payload.split('|', 1)

                    # 1) Resolver folder_id (None = raíz)
                    folder_id = None
                    ref = (carpeta_ref or '').strip()
                    if ref and ref.lower() != 'root':
                        if ref.isdigit():
                            folder_id = int(ref)
                        else:
                            # Resolver por nombre (único por propietario a este nivel; si no es único, error)
                            cursor.execute(
                                'SELECT id_carpeta FROM carpeta WHERE propietario = ? AND nombre = ?',
                                (propietario, ref)
                            )
                            rows = cursor.fetchall()
                            if len(rows) == 0:
                                response = 'ERR|Carpeta no encontrada'
                                # IMPORTANTE: hacer return para salir del bloque
                                # (si preferís, podés usar una excepción y capturarla abajo)
                                # pero aquí devolvemos directamente.
                                # --
                                # Nota: si tu modelo permite carpetas con el mismo nombre en distintos padres,
                                # este lookup por nombre sin especificar el padre puede ser ambiguo.
                                # En ese caso, conviene requerir ID.
                            elif len(rows) > 1:
                                response = 'ERR|Carpeta ambigua (varias con el mismo nombre). Usa ID.'
                            else:
                                folder_id = rows[0][0]

                    if response.startswith('ERR|'):  # ya definimos un error arriba
                        pass
                    else:
                        # 2) Listar carpetas hijas directas
                        if folder_id is None:
                            cursor.execute(
                                'SELECT id_carpeta, nombre, propietario, carpeta_padre '
                                'FROM carpeta WHERE propietario = ? AND carpeta_padre IS NULL',
                                (propietario,)
                            )
                        else:
                            cursor.execute(
                                'SELECT id_carpeta, nombre, propietario, carpeta_padre '
                                'FROM carpeta WHERE propietario = ? AND carpeta_padre = ?',
                                (propietario, folder_id)
                            )
                        carpetas = cursor.fetchall()
                        carpetas_str = '|'.join([f'{c[0]},{c[1]},{c[2]},{c[3]}' for c in carpetas])

                        # 3) Listar archivos directos
                        if folder_id is None:
                            cursor.execute(
                                'SELECT id_archivo, nombre, tipo, tamaño, fecha_subida, propietario, visibilidad, carpeta, ruta '
                                'FROM archivo WHERE propietario = ? AND carpeta IS NULL',
                                (propietario,)
                            )
                        else:
                            cursor.execute(
                                'SELECT id_archivo, nombre, tipo, tamaño, fecha_subida, propietario, visibilidad, carpeta, ruta '
                                'FROM archivo WHERE propietario = ? AND carpeta = ?',
                                (propietario, folder_id)
                            )
                        archivos = cursor.fetchall()
                        archivos_str = '|'.join([
                            f'{a[0]},{a[1]},{a[2]},{a[3]},{a[4]},{a[5]},{a[6]},{a[7]},{a[8]}'
                            for a in archivos
                        ])

                        # 4) Respuesta unificada
                        # Formato: OK|FOLDERS:<...>|FILES:<...>
                        # (Dejamos listas vacías si no hay resultados)
                        response = f'OK|FOLDERS:{carpetas_str}|FILES:{archivos_str}'

                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
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
                        # Resolver archivo garantizando pertenencia
                        if ref.isdigit():
                            cursor.execute(
                                'SELECT id_archivo, ruta FROM archivo WHERE id_archivo = ? AND propietario = ?',
                                (int(ref), propietario)
                            )
                        else:
                            # nombre es UNIQUE(nombre, propietario) según esquema
                            cursor.execute(
                                'SELECT id_archivo, ruta FROM archivo WHERE nombre = ? AND propietario = ?',
                                (ref, propietario)
                            )

                        row = cursor.fetchone()
                        if not row:
                            response = 'ERR|Archivo no encontrado para el propietario'
                        else:
                            archivo_id, ruta = row

                            # Borrar registro de la BDD
                            cursor.execute('DELETE FROM archivo WHERE id_archivo = ? AND propietario = ?',
                                           (archivo_id, propietario))
                            if cursor.rowcount == 0:
                                response = 'ERR|No se eliminó ningun archivo (no encontrado o sin permiso)'
                            else:
                                conn.commit()

                                # Intentar eliminar fichero en disco (si existe); no falla el proceso si no se puede borrar
                                try:
                                    if ruta and os.path.exists(ruta):
                                        os.remove(ruta)
                                except Exception as e:
                                    # devolver OK pero informar advertencia
                                    response = f'OK|Registro eliminado, fallo al borrar fichero en disco: {e}'
                                else:
                                    response = 'OK|Archivo eliminado'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'

            

            

            elif comando == 'upfil':
                try:
                    # Espera (TODO TEXTO / STR, sin bytes crudos):
                    # "nombre|tipo|tamaño|propietario|visibilidad|carpeta|<BASE64>"
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
                                # Decodificar Base64 -> bytes
                                try:
                                    contenido = base64.b64decode(contenido_b64, validate=True)
                                except Exception as e:
                                    response = f'ERR|Base64 inválido: {e}'
                                else:
                                    real_size = len(contenido)
                                    if tam_s and tam_s.isdigit() and int(tam_s) != real_size:
                                        response = f'ERR|Tamaño declarado ({tam_s}) no coincide con recibido ({real_size})'
                                    else:
                                        # --- Guardado en disco ---
                                        subdir = carpeta_str if carpeta_str else 'root'
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

                                        # carpeta NULL si raíz
                                        carpeta_val = None if carpeta_str == '' else carpeta_str
                                        
                                        if carpeta_val:
                                            cursor.execute(
                                                'SELECT 1 FROM carpeta WHERE nombre = ? AND propietario = ?',
                                                (carpeta_val, propietario)
                                            )
                                            carpeta_val = cursor.fetchone()[0]
                                            print(carpeta_val)
                                            if carpeta_val is None:
                                                raise Exception('Carpeta no existe')

                                        # --- Insert en BDD ---
                                        cursor.execute(
                                            'INSERT INTO archivo (nombre, tipo, tamaño, propietario, visibilidad, carpeta, ruta) '
                                            'VALUES (?, ?, ?, ?, ?, ?, ?)',
                                            (filename, tipo or 'application/octet-stream', real_size, propietario, visibilidad or 'private', carpeta_val, dest_path)
                                        )
                                        conn.commit()
                                        response = f'OK|Archivo subido|ruta={dest_path}'

                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'


            
            elif comando == 'dwfil':
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

            elif comando == 'renam':
                # payload:
                #   1) "nombre_actual|nuevo_nombre|propietario"
                #   2) "tipo|nombre_actual|nuevo_nombre|propietario"   (tipo: file/folder o f/d)
                try:
                    response = ''
                    parts = payload.split('|')

                    if len(parts) == 3:
                        tipo = ''  # se resolverá automáticamente
                        nombre_actual, nuevo_nombre, propietario = [p.strip() for p in parts]
                    elif len(parts) == 4:
                        nombre_actual, nuevo_nombre, propietario, tipo = [p.strip() for p in parts]
                        tipo = tipo.lower()
                        if tipo in ('f', 'file'):
                            tipo = 'file'
                        elif tipo in ('d', 'folder'):
                            tipo = 'folder'
                        else:
                            response = 'ERR|Tipo inválido (usa file/folder)'
                    else:
                        response = 'ERR|Payload inválido. Usa: nombre|nuevo|propietario  o  tipo|nombre|nuevo|propietario'

                    if not response:
                        if not nombre_actual or not nuevo_nombre or not propietario:
                            response = 'ERR|Nombre actual, nuevo nombre y propietario son obligatorios'
                        elif nombre_actual == nuevo_nombre:
                            response = 'OK|Sin cambios (el nombre es el mismo)'

                    # Resolver automáticamente si no se pasó tipo
                    if not response and not tipo:
                        # ¿Existe como archivo?
                        cursor.execute(
                            'SELECT id_archivo FROM archivo WHERE nombre = ? AND propietario = ? LIMIT 2',
                            (nombre_actual, propietario)
                        )
                        file_rows = cursor.fetchall()

                        # ¿Existe como carpeta?
                        cursor.execute(
                            'SELECT id_carpeta FROM carpeta WHERE nombre = ? AND propietario = ? LIMIT 2',
                            (nombre_actual, propietario)
                        )
                        folder_rows = cursor.fetchall()

                        total = (1 if file_rows else 0) + (1 if folder_rows else 0)
                        if total == 0:
                            response = 'ERR|No existe archivo ni carpeta con ese nombre para el propietario'
                        elif total > 1:
                            response = 'ERR|Nombre ambigua (existe archivo y carpeta). Especifica tipo (file/folder).'
                        else:
                            tipo = 'file' if file_rows else 'folder'

                    # Renombrar según tipo
                    if not response and tipo == 'file':
                        # Colisión: UNIQUE(nombre, propietario) en archivo
                        cursor.execute(
                            'SELECT 1 FROM archivo WHERE nombre = ? AND propietario = ?',
                            (nuevo_nombre, propietario)
                        )
                        if cursor.fetchone():
                            response = 'ERR|Ya existe un archivo con ese nombre para el propietario'
                        else:
                            cursor.execute(
                                'UPDATE archivo SET nombre = ? WHERE nombre = ? AND propietario = ?',
                                (nuevo_nombre, nombre_actual, propietario)
                            )
                            if cursor.rowcount == 0:
                                response = 'ERR|Archivo no encontrado o no pertenece al propietario'
                            else:
                                conn.commit()
                                response = 'OK|Archivo renombrado'

                    elif not response and tipo == 'folder':
                        # Colisión: UNIQUE(nombre, propietario) en carpeta
                        cursor.execute(
                            'SELECT 1 FROM carpeta WHERE nombre = ? AND propietario = ?',
                            (nuevo_nombre, propietario)
                        )
                        if cursor.fetchone():
                            response = 'ERR|Ya existe una carpeta con ese nombre para el propietario'
                        else:
                            cursor.execute(
                                'UPDATE carpeta SET nombre = ? WHERE nombre = ? AND propietario = ?',
                                (nuevo_nombre, nombre_actual, propietario)
                            )
                            if cursor.rowcount == 0:
                                response = 'ERR|Carpeta no encontrada o no pertenece al propietario'
                            else:
                                conn.commit()
                                response = 'OK|Carpeta renombrada'

                    # Respuesta final
                    if not response:
                        response = 'ERR|No se pudo determinar el tipo a renombrar'

                except sqlite3.IntegrityError as e:
                    response = f'ERR|{str(e)}'
                except sqlite3.Error as e:
                    response = f'ERR|{str(e)}'
                except Exception as e:
                    response = f'ERR|{str(e)}'



            elif comando == 'mvfil':
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


