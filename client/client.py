import shlex
import socket
import sys
import re
import os
import mimetypes
import base64
#from plyer import email

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bus_addr = ('localhost', 5000)
sock.connect(bus_addr)

"""
# cuando se inicia
1. Registrar usuario
2. Iniciar sesion

# cuando se inicia sesion
1. configuracion de cuenta
2. administracion de archivos
3. busqueda de archivo
4. historial

#config de cuenta
1. cambiar nombre
2. cambiar email
3. cambiar contraseña
4. cambiar rol
5. eliminar cuenta
6. cerrar sesion

#admin de archivos
1. crear carpeta
2. subir archivo
3. listar archivos
4. descargar archivo
5. eliminar archivo


"""










    
def iniciar_sesion():

    print("1. Registrar usuario \n"\
    "2. Iniciar sesion")

    accion = input("Elige una accion")
    if accion == "1":
        nombre = input("nombre")
        email = input("email")
        contraseña = input("contraseña")
        rol = input("rol (0: usuario, 1: admin)")

        length = 15 + len(nombre) + len(email) + len(contraseña) + len(rol)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthregis' + bytes(f'{nombre}|{email}|{contraseña}|{rol}', 'utf-8')

        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Checking server answer ...")
        print('received {!r}'.format(data))
        return data
    if accion == "2":
        email = input("Email: ")
        contraseña = input("Contraseña: ")

        length = 15 + len(email) + len(contraseña)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthlogin' + bytes(f'{email}|{contraseña}', 'utf-8')

        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Checking server answer ...")
        print('received {!r}'.format(data))
        return data

def paso2(user_id):
    print("1. Configuracion de cuenta \n" 
    "2. Administracion de archivos\n" 
    "3. Busqueda de archivos\n"    
    "4. Historial\n"
    "5. Etiquetas")
    accion2 = input("Elige una accion")
    if accion2 == "1":
        config_cuenta(user_id)
    elif accion2 == "2":
        admin_archivos(user_id)
    elif accion2 == "3":
        busquedaFiltrado(user_id)
    elif accion2 == "4":
        historial(user_id)
    elif accion2 == "5":
        menu_etiquetas(user_id)
    else:
        print("Accion no valida")

def busquedaFiltrado(user_id):
    """
    Selecciona la combinacion de numeros en orden de lo que quieres ver en el archivo buscado:
    1.- Orden en que ocurrieron los eventos
    2.- Fecha
    3.- comportamientos que el archivo a tenido
    4.- Tamaño
    5.- Ruta
    """
    print("Busqueda y Filtrado de Archivos")
    
    nombre_archivo = input("Nombre del archivo a buscar (o dejar en blanco para todos): ")
    
    print("Criterios de filtrado:")
    print("1. Orden en que ocurrieron los eventos")
    print("2. Fecha")
    print("3. Comportamientos que el archivo ha tenido")
    print("4. Tamaño")
    print("5. Ruta")
    
    criterios = input("Ingresa los números de los criterios (ej: 234): ")
    
    servicio = 'sbusq'
    comando = 'searc'
    payload = f'{user_id}|{nombre_archivo}|{criterios}'
    
    longitud_total = len(servicio) + len(comando) + len(payload)
    longitud_str = str(longitud_total).zfill(5)
    
    message = longitud_str.encode() + servicio.encode() + comando.encode() + payload.encode()
    print(f' Enviando: {message}')
    
    sock.sendall(message)
    
    amount_received = 0
    amount_expected = int(sock.recv(5))
    response_data = b''
    
    while amount_received < amount_expected:
        data = sock.recv(amount_expected - amount_received)
        response_data += data
        amount_received += len(data)
    
    print("Resultados de búsqueda:")
    
    # Procesar respuesta
    if response_data.startswith(b'OK|'):
        resultados = response_data[3:].decode()
        print(resultados)
    else:
        print(response_data.decode())
#
def historial(user_id):
    print("Historial de Actividades")
    
    servicio = 'shist'
    comando = 'getH '
    payload = user_id
    
    longitud_total = len(servicio) + len(comando) + len(payload)
    longitud_str = str(longitud_total).zfill(5)
    
    message = longitud_str.encode() + servicio.encode() + comando.encode() + payload.encode()
    print(f' Enviando: {message}')
    
    sock.sendall(message)
    
    amount_received = 0
    amount_expected = int(sock.recv(5))
    response_data = b''
    
    while amount_received < amount_expected:
        data = sock.recv(amount_expected - amount_received)
        response_data += data
        amount_received += len(data)
    
    print("Historial obtenido:")
    
    #  CORRECCIÓN: El bus envía shistOKdatos (UN solo OK)
    if response_data.startswith(b'shistOK'):
        historial_data = response_data[7:].decode()  # Quitar 'shistOK'
        print(historial_data)
    else:
        print("Error:", response_data.decode())

def config_cuenta(user_id):
    print("1. Cambiar nombre \n"\
        "2. Cambiar email \n"\
        "3. Cambiar contraseña \n"\
        "4. Eliminar cuenta \n"\
        "5. Cerrar sesion \n"\
        "6. Ver informacion de la cuenta")
    accion = input("Elige una accion")
    if accion == "1":
        nuevo_nombre = input("Nuevo nombre")
        length = 15 + len(user_id) + len(nuevo_nombre)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthcname' + bytes(f'{user_id}|{nuevo_nombre}', 'utf-8')
        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Respuesta del servidor:", data.decode())
    if accion == "2":
        nuevo_email = input("Nuevo email")
        length = 15 + len(user_id) + len(nuevo_email)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthcmail' + bytes(f'{user_id}|{nuevo_email}', 'utf-8')
        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Respuesta del servidor:", data.decode())
    if accion == "3":
        nueva_contraseña = input("Nueva contraseña")
        length = 15 + len(user_id) + len(nueva_contraseña)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthcpass' + bytes(f'{user_id}|{nueva_contraseña}', 'utf-8')
        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Respuesta del servidor:", data.decode())
    if accion == "4":
        confirmar = input("¿Estás seguro de que deseas eliminar tu cuenta? Esta acción es irreversible. (s/n)")
        if confirmar.lower() == 's':
            length = 15 + len(user_id)
            length_str = str(length).zfill(5)
            message = length_str.encode() + b'sauthdelac' + bytes(f'{user_id}', 'utf-8')
            sock.sendall(message)
            amount_received = 0
            amount_expected = int(sock.recv(5))
            while amount_received < amount_expected:
                data = sock.recv (amount_expected - amount_received)
                amount_received += len (data)
            print("Respuesta del servidor:", data.decode())
            sys.exit()
        else:
            print("Eliminación de cuenta cancelada.")
    if accion == "5":
        print("Cerrando sesion...")
        sys.exit()
        return
    if accion == "6":
        length = 15 + len(user_id)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthginfo' + bytes(f'{user_id}', 'utf-8')
        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Respuesta del servidor:", data.decode())

        user_info = data[10:].decode().split('|')
        print(user_info)
        print(f"ID: {user_info[0]}\nNombre: {user_info[1]}\nEmail: {user_info[2]}\nRol: {user_info[3]}\nFecha de creación: {user_info[4]}")


def send_request(service, command, payload):
    length = 15 + len(payload)
    length_str = str(length).zfill(5)

    if isinstance(payload, bytes):
        payload_bytes = payload
    else:
        payload_bytes = payload.encode()

    total_len = 15 + len(payload_bytes)

    # límite de 5 dígitos
    if total_len > 99999:
        raise ValueError(
            f"Mensaje demasiado grande ({total_len} bytes). "
            "Con header de 5 dígitos el máximo es 99,999."
        )

    message = length_str.encode() + service.encode() + command.encode() + payload_bytes
    sock.sendall(message)
    amount_received = 0
    amount_expected = int(sock.recv(5))
    while amount_received < amount_expected:
        data = sock.recv (amount_expected - amount_received)
        amount_received += len (data)
    return data

def _cmd_mkdir(user_id, args):
    if len(args) < 1:
        print("Uso: mkdir <nombre_carpeta> [CARPETA_PADRE]")
        return
    nombre_carpeta = args[0]
    carpeta_padre = args[1] if len(args) > 1 else ''
    response = send_request('sarch', 'mkdir', f'{nombre_carpeta}|{user_id}|{carpeta_padre}')
    print("Respuesta del servidor:", response.decode())

def _cmd_rmdir(user_id, args):
    if len(args) != 1:
        print("Uso: rmdir <Carpeta>")
        return
    carpeta = args[0]
    response = send_request('sarch', 'rmdir', f'{user_id}|{carpeta}')
    print("Respuesta del servidor:", response.decode())

def _cmd_ls(user_id, args):
    BLUE = "\033[34m"   # carpetas
    GREEN = "\033[32m"  # archivos
    RESET = "\033[0m"
    BOLD = "\033[1m"

    # Validación de argumentos
    if len(args) > 1:
        print("Uso: ls [Carpeta]")
        return
    carpeta = args[0] if args else ''

    # Petición al servidor
    response = send_request('sarch', 'lsall', f'{user_id}|{carpeta}')
    decoded = response.decode(errors='replace').strip()

    if not decoded.startswith('sarchOKOK|'):
        print(f"Error del servidor: {decoded}")
        return

    # Extraer carpetas y archivos
    try:
        sections = decoded.split('|')
        folders_str = next((s[8:] for s in sections if s.startswith('FOLDERS:')), '')
        files_str = next((s[6:] for s in sections if s.startswith('FILES:')), '')
    except Exception:
        print("Formato de respuesta inválido.")
        return

    folders = [f.split(',')[1] for f in folders_str.split('|') if f.strip()]
    files = [a.split(',')[1] for a in files_str.split('|') if a.strip()]

    # Carpetas en azul y archivos en verde
    for name in folders:
        print(f"{BLUE}{name}/{RESET}")
    for name in files:
        print(f"{GREEN}{name}{RESET}")
    print()

def _cmd_rm(user_id, args):
    if len(args) != 1:
        print("Uso: rm <nombre_archivo>")
        return
    archivo_nombre = args[0]
    response = send_request('sarch', 'rmfil', f'{user_id}|{archivo_nombre}')
    print("Respuesta del servidor:", response.decode())

def _cmd_upload(user_id, args):
    """
    Uso: upload <ruta_local> [nombre_carpeta]
    - Envía TODO como texto: metadatos + contenido en Base64 (compatible con bus str-only)
    - Servidor espera: "nombre|tipo|tamaño|propietario|visibilidad|carpeta|<BASE64>"
    """
    GREEN = "\033[32m"; RED = "\033[31m"; RESET = "\033[0m"
    def ok(msg): print(f"{GREEN}{msg}{RESET}")
    def err(msg): print(f"{RED}{msg}{RESET}")

    if not (1 <= len(args) <= 2):
        print("Uso: upload <ruta_local> [nombre_carpeta]")
        return

    ruta_local = args[0]
    carpeta_nombre = args[1] if len(args) == 2 else ""  # vacío = raíz

    if '|' in carpeta_nombre:
        err("El nombre de carpeta no puede contener '|'.")
        return

    try:
        with open(ruta_local, 'rb') as f:
            contenido = f.read()
    except FileNotFoundError:
        err(f"Archivo no encontrado: {ruta_local}")
        return
    except Exception as e:
        err(f"No se pudo leer el archivo: {e}")
        return

    nombre = os.path.basename(ruta_local).strip() or "archivo"
    if '|' in nombre:
        err("El nombre de archivo no puede contener '|'.")
        return

    mime, _ = mimetypes.guess_type(nombre)
    tipo = mime or 'application/octet-stream'
    tamaño = len(contenido)
    visibilidad = 'private'

    # Codificar binario a Base64 (ASCII seguro)
    contenido_b64 = base64.b64encode(contenido).decode('ascii')

    # Armar payload TODO TEXTO
    payload = f"{nombre}|{tipo}|{tamaño}|{user_id}|{visibilidad}|{carpeta_nombre}|{contenido_b64}"

    try:
        resp = send_request('sarch', 'upfil', payload)  # send_request debe aceptar str (lo encodea internamente)
        decoded = resp.decode(errors='replace').strip()
    except Exception as e:
        err(f"Error al enviar: {e}")
        return

    if decoded.startswith("sarchOKOK|") or decoded.startswith("OK|"):
        ok(decoded.replace("sarchOKOK|", "").replace("OK|", ""))
    else:
        err(decoded)

def _cmd_dw(user_id, args):
    """
    Uso:
      download <archivo_ref> [ruta_destino]
    - <archivo_ref> puede ser ID numérico o nombre de archivo.
    - Si no pasas ruta_destino, se usa el nombre que llega desde el servidor (NAME).
    - Si ruta_destino es un directorio, guardamos como <ruta_destino>/<NAME>.
    """
    GREEN = "\033[32m"; RED = "\033[31m"; RESET = "\033[0m"
    def ok(msg): print(f"{GREEN}{msg}{RESET}")
    def err(msg): print(f"{RED}{msg}{RESET}")

    if not (1 <= len(args) <= 2):
        print("Uso: download <archivo_ref> [ruta_destino]")
        return

    archivo_ref = args[0]
    ruta_destino_arg = args[1] if len(args) == 2 else None

    # 1) Pedir al servidor: payload "propietario|archivo_ref"
    payload = f"{user_id}|{archivo_ref}"
    resp = send_request('sarch', 'dwfil', payload)
    decoded = resp.decode('utf-8', errors='replace').strip()

    # 2) Validar respuesta
    if decoded.startswith('sarchOKOK|'):
        decoded = decoded[len('sarchOKOK|'):]
    elif decoded.startswith('OK|'):
        decoded = decoded[3:]
    else:
        err(f"Error del servidor: {decoded}")
        return

    # 3) Separar metadatos de B64
    #    Estructura: NAME:...|TYPE:...|SIZE:...|DATE:...|B64:<base64>
    #    Cortamos por '|B64:' para no romper el base64 si trae '|'
    try:
        meta_part, b64_part = decoded.split('|B64:', 1)
    except ValueError:
        err("Respuesta inválida (no se encontró B64).")
        return

    # Parsear metadatos
    meta = {}
    for chunk in meta_part.split('|'):
        if ':' in chunk:
            k, v = chunk.split(':', 1)
            meta[k] = v

    name = meta.get('NAME') or 'archivo'
    mime = meta.get('TYPE') or 'application/octet-stream'
    size_s = meta.get('SIZE') or '0'
    try:
        size_expected = int(size_s)
    except ValueError:
        size_expected = None

    # 4) Decodificar base64
    try:
        data = base64.b64decode(b64_part, validate=True)
    except Exception as e:
        err(f"Base64 inválido: {e}")
        return

    if size_expected is not None and size_expected != len(data):
        err(f"Tamaño no coincide (esperado={size_expected}, recibido={len(data)}).")
        return

    # 5) Resolver ruta de guardado
    if ruta_destino_arg is None or ruta_destino_arg.strip() == '':
        # Guardar con el nombre que vino del server en el directorio actual
        ruta_destino = os.path.abspath(name)
    else:
        ruta_destino_arg = os.path.abspath(ruta_destino_arg)
        if os.path.isdir(ruta_destino_arg):
            ruta_destino = os.path.join(ruta_destino_arg, name)
        else:
            # Si no existe el dir padre, créalo
            parent = os.path.dirname(ruta_destino_arg)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            ruta_destino = ruta_destino_arg

    # 6) Escribir archivo
    try:
        with open(ruta_destino, 'wb') as f:
            f.write(data)
    except Exception as e:
        err(f"No se pudo escribir el archivo: {e}")
        return

    ok(f"Archivo descargado en: {ruta_destino}  ({len(data)} bytes, {mime})")

def _cmd_rename(user_id, args):
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    def ok(msg): print(f"{GREEN}{msg}{RESET}")
    def err(msg): print(f"{RED}{msg}{RESET}")

    if len(args) < 2 or len(args) > 3:
        print("Uso: rename <nombre_archivo_o_carpeta> <nuevo_nombre> [file | folder]")
        return

    nombre_actual, nuevo_nombre = args[:2]
    tipo = args[2] if len(args) == 3 else None
    nombre_actual = nombre_actual.strip()
    nuevo_nombre = nuevo_nombre.strip()

    if not nombre_actual or not nuevo_nombre:
        err("Los nombres no pueden estar vacíos.")
        return

    
    payload = f"{nombre_actual}|{nuevo_nombre}|{user_id}|{tipo}"
    response = send_request("sarch", "renam", payload).decode(errors="replace").strip()

    if response.startswith("sarchOKOK|"):
        ok(response.replace("sarchOKOK|", "").replace("OK|", ""))
    else:
        err(response)

def _cmd_mv(user_id, args):
    if len(args) != 2:
        print("Uso: mv <nombre archivo|carpeta> <nueva_carpeta>")
        return
    nombre_archivo_o_carpeta, nueva_carpeta = args
    response = send_request('sarch', 'movef', f'{user_id}|{nombre_archivo_o_carpeta}|{nueva_carpeta}')
    print("Respuesta del servidor:", response.decode())

COMMANDS = {
    'mkdir': _cmd_mkdir,
    'rmdir': _cmd_rmdir,
    'ls': _cmd_ls,
    'rm': _cmd_rm,
    'upload': _cmd_upload,
    'download': _cmd_dw,
    'rename': _cmd_rename,
    'mv': _cmd_mv,
    'help': lambda user_id, args: print(
"""Comandos:
" mkdir <nombre_carpeta> [CARPETA_PADRE]
" rmdir <Carpeta>
" ls [Carpeta]
" rm <nombre_archivo>
" upload <ruta_local> [nombre_carpeta]
" download <archivo_ref> [ruta_destino]
" rename <nombre_archivo_o_carpeta> <nuevo_nombre> [file | folder]
" mv <nombre archivo|carpeta> <nueva_carpeta>
" exit / quit
"""
            ),
}

def admin_archivos(user_id):
    print("Shell de archivos. Escribe 'help' para ver comandos.")

    while True:
        try:
            line = input("> ")
        except EOFError:
            print() # salto de línea al salir con Ctrl-D
            break
        except KeyboardInterrupt:
            print() # salto de línea al salir con Ctrl-C
            break
        line = line.strip()
        if not line:
            continue
        if line in ('exit', 'quit'):
            print("Saliendo de la administracion de archivos.")
            break

        try:
            parts = shlex.split(line)
        except ValueError as e:
            print(f"Error al parsear el comando: {e}")
            continue

        cmd, *args = parts
        handler = COMMANDS.get(cmd)
        if not handler:
            print(f"Comando desconocido: {cmd}. Escribe 'help' para ver comandos.")
            continue
        try:
            handler(user_id, args)
        except Exception as e:
            print(f"Error al ejecutar el comando '{cmd}': {e}")


SERVICE_TAG = '_tag_'

def crear_etiqueta(user_id):
    nombre = input("Ingrese nombre de la etiqueta: ")
    color = input("Ingrese color (por ejemplo #FF0000 o azul): ")
    payload = f"{user_id}|{nombre}|{color}"
    response = send_request(SERVICE_TAG, "creat", payload)
    print(f" Respuesta: {response}")

def ver_etiquetas(user_id):
    response = send_request(SERVICE_TAG, "read ", str(user_id))
    print(f" Etiquetas del usuario {user_id}:")
    print(response)

def actualizar_etiqueta(user_id):
    id_etiqueta = input("Ingrese ID de la etiqueta a actualizar: ")
    nuevo_nombre = input("Nuevo nombre: ")
    nuevo_color = input("Nuevo color: ")
    payload = f"{user_id}|{id_etiqueta}|{nuevo_nombre}|{nuevo_color}"
    response = send_request(SERVICE_TAG, "updat", payload)
    print(f" Respuesta: {response}")

def eliminar_etiqueta(user_id):
    id_etiqueta = input("Ingrese ID de la etiqueta a eliminar: ")
    payload = f"{user_id}|{id_etiqueta}"
    response = send_request(SERVICE_TAG, "del  ", payload)
    print(f" Respuesta: {response}")

def vincular_etiqueta():
    id_archivo = input("Ingrese ID del archivo: ")
    id_etiqueta = input("Ingrese ID de la etiqueta: ")
    payload = f"{id_archivo}|{id_etiqueta}"
    response = send_request(SERVICE_TAG, "link ", payload)
    print(f" Respuesta: {response}")

def listar_etiquetas_archivo():
    id_archivo = input("Ingrese ID del archivo: ")
    response = send_request(SERVICE_TAG, "listr", id_archivo)
    print(f" Etiquetas asociadas al archivo {id_archivo}:")
    print(response)


def menu_etiquetas(user_id):

    print(" CLIENTE DE ETIQUETAS")

    #user_id = input("Ingrese su ID de usuario: ")

    while True:
        print("\n MENÚ DE ETIQUETAS")
        print("1. Crear etiqueta")
        print("2. Ver etiquetas del usuario")
        print("3. Actualizar etiqueta")
        print("4. Eliminar etiqueta")
        print("5. Vincular etiqueta a archivo")
        print("6. Listar etiquetas de un archivo")
        print("7. Salir")

        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            crear_etiqueta(user_id)
        elif opcion == "2":
            ver_etiquetas(user_id)
        elif opcion == "3":
            actualizar_etiqueta(user_id)
        elif opcion == "4":
            eliminar_etiqueta(user_id)
        elif opcion == "5":
            vincular_etiqueta()
        elif opcion == "6":
            listar_etiquetas_archivo()
        elif opcion == "7":
            print("Saliendo del cliente de etiquetas")
            break
        else:
            print("Opción no válida")


def admin_menu(user_id):
    while True:
        print("\n----MENU ADMINISTRADOR ----")
        print("1. Eliminar cuenta de usuario")
        print("2. Consultar información de usuario")
        print("3. Listar usuarios")
        print("4. Salir")

        opcion = input("Selecciona una opción: ")


        if opcion == '1':
            target_id = input("ID del usuario a eliminar: ")
            payload = f"{user_id}|{target_id}"
            response = send_request('admin', 'delac', payload).decode()
            print(" Respuesta:", response)

        elif opcion == '2':
            target_id = input("ID del usuario a consultar: ")
            payload = f"{user_id}|{target_id}"
            response = send_request('admin', 'ginfo', payload)
            print(" Respuesta:", response)

        elif opcion == '4':
            print(" Saliendo del modo administrador...")
            break

        elif opcion == '3':
            response = send_request('admin', 'listu', '').decode()
            print(response)
            if response.startswith('adminOKOK|'):
                users = response[3:].split('|')
                print("\nID | Nombre")
                print("-"*20)
                for u in users:
                    if not u.strip() or ':' not in u:  
                        continue
                    uid, name = u.split(':', 1)
                    print(f"{uid:<3} | {name}")
            else:
                print(" Error al listar usuarios:", response)



if __name__ == "__main__": 
    try:
        while True:
            data = iniciar_sesion()

            text = data.decode()

            if text.startswith("sauthOKOK|"):
                parts = text.split('|')

                user_id = parts[1]
                rol = parts[2].strip() if len(parts) > 2 else "user"

                print(f" Login exitoso. Usuario ID: {user_id}, Rol: {rol}")

                if rol == "1":
                    print("Bienvenido al menu de administrador")
                    admin_menu(user_id)
                else:
                    print("Bienvenido al menu de usuario")
                    paso2(user_id)

                break

            else:
                print("Login fallido:", text)

    finally:
        sock.close()


