import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

bus_addr = ('localhost', 5000)
sock.connect(bus_addr)

try:
    service = 'shist'

    message = b'00010sinit' + service.encode()
    
    sock.sendall(message)
    sinit = 1

    while True:
        print('Esperando mensaje historial...')
        amount_received = 0
        amount_expected = int(sock.recv(5))

        while amount_received < amount_expected:
            data = sock.recv(amount_expected - amount_received)
            amount_received += len(data)

        if sinit == 1:
            sinit = 0
            print('Servicio historial iniciado')
            continue
        
        elif data[:5].decode() == 'shist':
            print(f'Mensaje recibido: {data}')
            comando = data[5:10].decode()
            user_id = data[10:].decode()

            print(f'Comando: {comando}, User ID: {user_id}')

            if comando == 'getH ':
                try:
                    # Consultar base de datos a través del bus
                    db_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    db_sock.connect(('localhost', 5000))
                    
                    consulta = "SELECT accion, fecha, entidad_afectada FROM historial WHERE usuario = ? ORDER BY fecha DESC LIMIT 10"
                    parametros = [user_id]
                    payload_db = f"{consulta}|{parametros}"
                    longitud_total = len(payload_db) + 10
                    longitud_str = str(longitud_total).zfill(5)
                    
                    message_db = longitud_str.encode() + b'sbasequery' + payload_db.encode()
                    print(f'Consultando base de datos: {message_db}')
                    db_sock.sendall(message_db)
                    
                    # Recibir respuesta
                    amount_received_db = 0
                    amount_expected_db = int(db_sock.recv(5))
                    response_data_db = b''
                    
                    while amount_received_db < amount_expected_db:
                        data_db = db_sock.recv(amount_expected_db - amount_received_db)
                        response_data_db += data_db
                        amount_received_db += len(data_db)
                    
                    db_sock.close()
                    
                    print(f'Respuesta de base de datos: {response_data_db}')
                    
                    # Procesar respuesta de sbase
                    if response_data_db.startswith(b'sbaseOK'):
                        datos = response_data_db[7:].decode()
                        print(f'Datos recibidos: {datos}')
                        
                        try:
                            historial_data = eval(datos)
                            if historial_data:
                                resultado = " Historial de actividades:\n"
                                resultado += "=" * 50 + "\n"
                                for accion, fecha, entidad in historial_data:
                                    resultado += f" Fecha: {fecha}\n"
                                    resultado += f" Acción: {accion}\n"
                                    resultado += f" Entidad: {entidad}\n"
                                    resultado += "-" * 30 + "\n"
                                
                                #  CORRECCIÓN: NO incluir "OK", solo los datos
                                # El bus agregará el "OK" automáticamente
                                response_content = f'{resultado}'
                            else:
                                response_content = 'No hay historial disponible para este usuario'
                        except Exception as e:
                            response_content = f'ERR|Error procesando datos: {str(e)}'
                    else:
                        response_content = 'ERR|Error en la consulta a la base de datos'
                        
                except Exception as e:
                    response_content = f'ERR|{str(e)}'

            else:
                response_content = 'ERR|Comando no reconocido'

            #  CORRECCIÓN CRÍTICA: Enviar SIN "OK"
            # El bus agregará el "OK" automáticamente
            full_response = service + response_content
            response_message = f'{len(full_response):05}'.encode() + full_response.encode()
            
            print(f'Enviando respuesta: {response_message}')
            sock.sendall(response_message)

finally:
    print('closing socket')
    sock.close()