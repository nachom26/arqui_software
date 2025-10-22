import socket

SERVICE_NAME = '_tag_'
DB_SERVICE = 'sbase' 

print(f" INICIANDO SERVICIO DE ETIQUETAS: {SERVICE_NAME}")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost', 5000))

sinit_msg = b'00010sinit' + SERVICE_NAME.encode()
print(f" Registrando servicio en bus: {sinit_msg}")
sock.sendall(sinit_msg)

length = sock.recv(5)
if length:
    response = sock.recv(int(length))
    print(f" Confirmación: {response}")

print(f"{SERVICE_NAME} LISTO - Esperando mensajes...")

def send_to_db(command, sql, params=None):
    if params is None:
        params = []
    payload = f"{sql}|{params}"
    full_msg = f"{len(DB_SERVICE + command + payload):05}".encode() + (DB_SERVICE + command + payload).encode()
    sock.sendall(full_msg)

    length_data = sock.recv(5)
    if not length_data:
        return "Error: sin respuesta de DB"
    data_len = int(length_data)
    data = sock.recv(data_len).decode()
    return data

try:
    while True:
        print("Esperando mensaje...")
        length_data = sock.recv(5)
        if not length_data:
            print(" Conexión cerrada")
            break

        total_len = int(length_data)
        data = b''
        while len(data) < total_len:
            chunk = sock.recv(total_len - len(data))
            data += chunk

        print(f"Mensaje recibido: {data}")
        data = data.decode()

        command = None
        payload = None
        if data.startswith(SERVICE_NAME):
            command = data[len(SERVICE_NAME):len(SERVICE_NAME)+5]
            payload = data[len(SERVICE_NAME)+5:]

        if not command:
            print(" Formato no reconocido")
            continue

        print(f" Comando: {command}, Payload: {payload}")

       
        if command == 'creat':
            user_id, nombre, color = payload.split('|')
            sql = "INSERT INTO etiqueta (nombre, color, propietario) VALUES (?, ?, ?)"
            params = [nombre, color, int(user_id)]
            response = send_to_db('query', sql, params)
            print(f"Respuesta DB: {response}")
            response_msg = f"{SERVICE_NAME}OK|Etiqueta creada correctamente"

        elif command == 'read ':
            user_id = payload.strip()
            sql = "SELECT id_etiqueta, nombre, color, propietario FROM etiqueta WHERE propietario = ?"
            params = [int(user_id)]
            response = send_to_db('query', sql, params)
            print(f"Respuesta DB: {response}")
            response_msg = f"{SERVICE_NAME}OKOK|{response}"

        elif command == 'updat':
            user_id, id_etiqueta, nuevo_nombre, nuevo_color = payload.split('|')
            sql = "UPDATE etiqueta SET nombre = ?, color = ? WHERE id_etiqueta = ? AND propietario = ?"
            params = [nuevo_nombre, nuevo_color, int(id_etiqueta), int(user_id)]
            response = send_to_db('query', sql, params)
            print(f"Respuesta DB: {response}")
            response_msg = f"{SERVICE_NAME}OK|Etiqueta actualizada"

        elif command == 'del  ':
            user_id, id_etiqueta = payload.split('|')
            sql = "DELETE FROM etiqueta WHERE id_etiqueta = ? AND propietario = ?"
            params = [int(id_etiqueta), int(user_id)]
            response = send_to_db('query', sql, params)
            print(f"Respuesta DB: {response}")
            response_msg = f"{SERVICE_NAME}OK|Etiqueta eliminada"
            
        elif command == 'link ':
            id_archivo, id_etiqueta = payload.split('|')
            sql = "INSERT INTO archivo_etiqueta (id_archivo, id_etiqueta) VALUES (?, ?)"
            params = [int(id_archivo), int(id_etiqueta)]
            response = send_to_db('query', sql, params)
            response_msg = f"{SERVICE_NAME}OK|Etiqueta vinculada a archivo"

        # Ver etiquetas 
        elif command == 'listr':
            id_archivo = payload.strip()
            sql = """
                SELECT e.id_etiqueta, e.nombre, e.color
                FROM etiqueta e
                JOIN archivo_etiqueta ae ON e.id_etiqueta = ae.id_etiqueta
                WHERE ae.id_archivo = ?
            """
            params = [int(id_archivo)]
            response = send_to_db('query', sql, params)
            response_msg = f"{SERVICE_NAME}OK|{response}"

        else:
            response_msg = f"{SERVICE_NAME}ERR|Comando no reconocido: {command}"

        # Enviar respuesta al bus
        final_msg = f"{len(response_msg):05}".encode() + response_msg.encode()
        sock.sendall(final_msg)
        print(f"Respuesta enviada al bus: {final_msg}")

except Exception as e:
    print(f" Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    sock.close()
    print("Servicio cerrado")