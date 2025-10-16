import socket
import sys

from plyer import email

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
    
    print("1. Configuracion de cuenta \n"\
    "2. Administracion de archivos")
    accion2 = input("Elige una accion")
    if accion2 == "1":
        config_cuenta(user_id)

    elif accion2 == "2":
        admin_archivos(user_id)
    else:
        print("Accion no valida")


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

def admin_archivos():
    print("1 -> Crear carpeta \n"
        "2 -> Subir archivo \n"
        "ls -> Listar archivos \n"
        "4 -> Descargar archivo \n"
        "5 -> Eliminar archivo")
    accion = input("Elige una accion")
    if accion == "1":
        nombre_carpeta = input("Nombre de la carpeta")
        propietario = email
        carpeta_padre = input("Carpeta padre (opcional, dejar en blanco si no aplica)")
        length = 15 + len(nombre_carpeta) + len(propietario) + len(carpeta_padre)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sarchcreatefold' + bytes(f'{nombre_carpeta}|{propietario}|{carpeta_padre}', 'utf-8')
        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Respuesta del servidor:", data.decode())

    if accion == "2":
        ruta_archivo = input("Ruta del archivo a subir")
        nombre_archivo = ruta_archivo.split('/')[-1]
        propietario = email
        carpeta_destino = input("Carpeta destino (opcional, dejar en blanco si no aplica)")
        try:
            with open(ruta_archivo, 'rb') as f:
                contenido = f.read()
            length = 15 + len(nombre_archivo) + len(propietario) + len(carpeta_destino) + len(contenido)
            length_str = str(length).zfill(5)
            message = length_str.encode() + b'sarchuploadfile' + bytes(f'{nombre_archivo}|{propietario}|{carpeta_destino}|', 'utf-8') + contenido
            sock.sendall(message)
            amount_received = 0
            amount_expected = int(sock.recv(5))
            while amount_received < amount_expected:
                data = sock.recv (amount_expected - amount_received)
                amount_received += len (data)
            print("Respuesta del servidor:", data.decode())
        except FileNotFoundError:
            print("Archivo no encontrado. Asegúrate de que la ruta es correcta.")
    
    if accion == "3":
        propietario = email
        length = 15 + len(propietario)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sarchlistfiles' + bytes(f'{propietario}', 'utf-8')
        sock.sendall(message)
        amount_received = 0
        amount_expected = int(sock.recv(5))
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Respuesta del servidor:", data.decode())

try:

    while True:

        data = iniciar_sesion()
        
        if data[5:7].decode() == 'OK' and data[7:9].decode() == 'OK':
            break

        print("Login fallido:", data.decode())
        
    user_id = data.split(b'|')[1].decode()
    print("Login exitoso")

    while True:
        paso2(user_id)


finally:
    sock.close()


