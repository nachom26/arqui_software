import socket

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





print("1. Registrar usuario \n"\
"2. Iniciar sesion")

try:
    accion = input("Elige una accion")
    if accion == "1":
        nombre = input("nombre")
        email = input("email")
        contraseña = input("contraseña")
        rol = input("rol")

        length = 10 + len(nombre) + len(email) + len(contraseña) + len(rol)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthcreateuser' + bytes(f'{nombre}|{email}|{contraseña}|{rol}', 'utf-8')

        sock.sendall(message)
        response = sock.recv(1024)
        print("Respuesta del servidor:", response.decode())

    if accion == "2":
        email = input("email")
        contraseña = input("contraseña")

        length = 10 + len(email) + len(contraseña)
        length_str = str(length).zfill(5)
        message = length_str.encode() + b'sauthloginusers' + bytes(f'{email}|{contraseña}', 'utf-8')

        sock.sendall(message)
        print("sent")
        amount_received = 0
        amount_expected = int(sock.recv(5))
        print("Expecting ", amount_expected)
        while amount_received < amount_expected:
            data = sock.recv (amount_expected - amount_received)
            amount_received += len (data)
        print("Checking server answer ...")
        print('received {!r}'.format(data))

finally:
    sock.close()


