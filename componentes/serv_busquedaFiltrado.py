import socket
import sqlite3

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

bus_addr = ('localhost', 5000)
sock.connect(bus_addr)

try:
    service = 'sbusq'

    message = b'00010sinit' + service.encode()
    
    sock.sendall(message)
    sinit = 1

    while True:
        print('Esperando mensaje busqueda...')
        amount_received = 0
        amount_expected = int(sock.recv(5))

        while amount_received < amount_expected:
            data = sock.recv(amount_expected - amount_received)
            amount_received += len(data)

        if sinit == 1:
            sinit = 0
            print('Servicio busqueda iniciado')
            continue
        
        elif data[:5].decode() == 'sbusq':
            print('Mensaje recibido busqueda:', data)
            comando = data[5:10].decode()
            payload = data[10:].decode()

            if comando == 'searc':
                try:
                    # Formato: user_id|nombre_archivo|criterios
                    partes = payload.split('|')
                    user_id = partes[0]
                    nombre_archivo = partes[1] if len(partes) > 1 else ""
                    criterios = partes[2] if len(partes) > 2 else ""
                    
                    print(f'Búsqueda - Usuario: {user_id}, Archivo: {nombre_archivo}, Criterios: {criterios}')
                    
                    # Construir consulta
                    base_query = "SELECT nombre, tipo, tamaño, fecha_subida, ruta FROM archivo WHERE propietario = ?"
                    params = [user_id]
                    
                    if nombre_archivo and nombre_archivo.strip():
                        base_query += " AND nombre LIKE ?"
                        params.append(f"%{nombre_archivo}%")
                    
                    # Aplicar criterios de ordenamiento
                    if '1' in criterios:
                        base_query += " ORDER BY fecha_subida DESC"
                    elif '2' in criterios:
                        base_query += " ORDER BY fecha_subida ASC" 
                    elif '3' in criterios:
                        base_query += " ORDER BY tipo"
                    elif '4' in criterios:
                        base_query += " ORDER BY tamaño DESC"
                    elif '5' in criterios:
                        base_query += " ORDER BY nombre"
                    else:
                        base_query += " ORDER BY fecha_subida DESC"
                    
                    # Conectar al bus para consultar sbase
                    db_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    db_sock.connect(('localhost', 5000))
                    
                    # Formatear mensaje para sbase
                    payload_db = f"{base_query}|{params}"
                    longitud_total = len(payload_db) + 10
                    longitud_str = str(longitud_total).zfill(5)
                    
                    message_db = longitud_str.encode() + b'sbasequery' + payload_db.encode()
                    print(f'Enviando a sbase: {message_db}')
                    db_sock.sendall(message_db)
                    
                    # Recibir respuesta de sbase
                    amount_received_db = 0
                    amount_expected_db = int(db_sock.recv(5))
                    response_data_db = b''
                    
                    while amount_received_db < amount_expected_db:
                        data_db = db_sock.recv(amount_expected_db - amount_received_db)
                        response_data_db += data_db
                        amount_received_db += len(data_db)
                    
                    db_sock.close()
                    
                    print(f'Respuesta de sbase: {response_data_db}')
                    
                    # Procesar respuesta
                    response_str = response_data_db.decode()
                    
                    if response_str.startswith('sbaseOK|'):
                        datos_str = response_str[8:]
                        print(f'Datos recibidos: {datos_str}')
                        
                        try:
                            archivos_data = eval(datos_str)
                            
                            if not archivos_data:
                                response = 'OK|No se encontraron archivos con los criterios especificados'
                            else:
                                resultado = "🔍 Resultados de búsqueda:\n"
                                resultado += "=" * 50 + "\n"
                                
                                for nombre, tipo, tamaño, fecha, ruta in archivos_data:
                                    resultado += f" {nombre}\n"
                                    resultado += f"    Tipo: {tipo}\n"
                                    resultado += f"    Tamaño: {tamaño} bytes\n" 
                                    resultado += f"    Fecha: {fecha}\n"
                                    if '5' in criterios:
                                        resultado += f"    Ruta: {ruta}\n"
                                    resultado += "-" * 30 + "\n"
                                
                                response = f'OK|{resultado}'
                        except Exception as e:
                            response = f'ERR|Error procesando datos: {str(e)}'
                            
                    elif response_str.startswith('sbaseERR|'):
                        error_msg = response_str[9:]
                        response = f'ERR|Error en base de datos: {error_msg}'
                    else:
                        response = f'ERR|Respuesta inesperada: {response_str}'
                        
                except Exception as e:
                    response = f'ERR|Error en búsqueda: {str(e)}'

            else:
                response = 'ERR|Comando no reconocido'

            response_message = f'{len(response):05}{service}{response}'.encode()
            print(f'Enviando respuesta: {response_message}')
            sock.sendall(response_message)

finally:
    print('closing socket busqueda')
    sock.close()
