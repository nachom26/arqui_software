import socket
import ast

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bus_addr = ('localhost', 5000)
sock.connect(bus_addr)


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Socket cerrado mientras se recibía la respuesta")
        buf += chunk
    return buf

def send_bus(sock: socket.socket, service: str, command: str, payload: str) -> bytes:
    svc = service.encode('ascii', 'ignore')
    cmd = command.encode('ascii', 'ignore')[:5].ljust(5, b' ')
    body = svc + cmd + payload.encode('utf-8')
    header = f"{len(body):05}".encode('ascii')
    sock.sendall(header + body)

    resp_len = int(_recv_exact(sock, 5).decode('ascii'))
    data = _recv_exact(sock, resp_len)
    if data.startswith(svc):
        return data[len(svc):]
    return data

def db_query(sock, sql: str, params=None, service: str = 'sbase'):
    payload = f"{sql}|{repr(list(params))}" if params else f"{sql}|"
    raw = send_bus(sock, service, 'query', payload)
    text = raw.decode('utf-8', 'replace').strip()

    if 'ERR|' in text:
        err_idx = text.find('ERR|')
        raise RuntimeError(text[err_idx:])

    if text.startswith('OK'):
        text = text[2:].lstrip('|').strip()

    if sql.lstrip().upper().startswith('SELECT'):
        if not text or text == 'OK':
            return []
        try:
            return ast.literal_eval(text)
        except Exception:
            return []
    else:
        return text

service = 'admin'
message = b'00010sinit' + service.encode()
sock.sendall(message)
sinit = 1

print("Servicio 'admin' iniciado y conectado al bus.")


try:
    while True:
        print("\n Esperando mensaje...")
        amount_expected = int(sock.recv(5))
        data = _recv_exact(sock, amount_expected)

        if sinit == 1:
            sinit = 0
            continue

        if not data.startswith(service.encode()):
            continue  

        print("Mensaje recibido:", data)
        comando = data[len(service):len(service)+5].decode().strip()
        payload = data[len(service)+5:].decode().strip()
        response = ""

        try:

            # eliminar cuenta 
            if comando == 'delac':
                admin_id, target_id = payload.split('|')
                db_query(sock, 'DELETE FROM usuarios WHERE id_usuario = ?', [target_id], service='sbase')
                response = 'OK|Usuario eliminado correctamente'

            #  consultar info
            elif comando == 'ginfo':
                admin_id, target_id = payload.split('|')
                rows = db_query(sock,
                                'SELECT id_usuario, nombre, email, rol FROM usuarios WHERE id_usuario = ?',
                                [target_id], service='sbase')
                if rows:
                    u = rows[0]
                    response = f'OK|ID:{u[0]}|Nombre:{u[1]}|Email:{u[2]}|Rol:{u[3]}'
                else:
                    response = 'ERR|Usuario no encontrado'

            # lista
            elif comando == 'listu':
                rows = db_query(sock, 'SELECT id_usuario, nombre FROM usuarios', [], service='sbase')
                if rows:
                    lista = '|'.join(f"{r[0]}:{r[1]}" for r in rows)
                    response = f'OK|{lista}'
                else:
                    response = 'OK|'  


        except Exception as e:
            response = f'ERR|{str(e)}'

        # enviar respuesta al bus
        response_msg = f'{len(response):05}{service}{response}'.encode()
        sock.sendall(response_msg)
        print("Respuesta enviada:", response)

finally:
    print("Cerrando socket.")
    sock.close()