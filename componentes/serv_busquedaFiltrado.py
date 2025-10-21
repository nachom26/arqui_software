import socket

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
            print(f'Mensaje recibido: {data}')
            comando = data[5:10].decode()
            payload = data[10:].decode()

            if comando == 'searc':
                try:
                    # Formato: user_id|nombre_archivo|criterios
                    partes = payload.split('|')
                    user_id = partes[0] if len(partes) > 0 else ""
                    nombre_archivo = partes[1] if len(partes) > 1 else ""
                    criterios = partes[2] if len(partes) > 2 else ""
                    
                    print(f'Búsqueda - Usuario: {user_id}, Archivo: "{nombre_archivo}", Criterios: {criterios}')
                    
                    # Construir consulta base
                    base_query = "SELECT nombre, tipo, tamaño, fecha_subida, ruta FROM archivo WHERE propietario = ?"
                    params = [user_id]
                    
                    # Agregar filtro por nombre si se especificó
                    if nombre_archivo and nombre_archivo.strip():
                        base_query += " AND nombre LIKE ?"
                        params.append(f"%{nombre_archivo}%")
                    
                    # Aplicar criterios de ordenamiento
                    if '1' in criterios:  # Fecha descendente
                        base_query += " ORDER BY fecha_subida DESC"
                    elif '2' in criterios:  # Fecha ascendente
                        base_query += " ORDER BY fecha_subida ASC"
                    elif '3' in criterios:  # Tipo
                        base_query += " ORDER BY tipo"
                    elif '4' in criterios:  # Tamaño
                        base_query += " ORDER BY tamaño DESC"
                    elif '5' in criterios:  # Nombre
                        base_query += " ORDER BY nombre"
                    else:  # Por defecto: fecha descendente
                        base_query += " ORDER BY fecha_subida DESC"
                    
                    print(f"🔍 Consulta SQL: {base_query}")
                    print(f"🔍 Parámetros: {params}")
                    
                    # Consultar base de datos
                    db_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    db_sock.connect(('localhost', 5000))
                    
                    payload_db = f"{base_query}|{params}"
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
                    
                    print(f'📥 Respuesta de base de datos: {response_data_db}')
                    
                    # ✅ CORRECCIÓN: Procesar respuesta correctamente
                    if response_data_db.startswith(b'sbaseOK'):
                        datos = response_data_db[7:].decode()  # Quitar 'sbaseOK'
                        print(f'📊 Datos recibidos: {datos}')
                        
                        try:
                            archivos_data = eval(datos)
                            
                            if archivos_data:
                                resultado = "🔍 Resultados de búsqueda:\n"
                                resultado += "=" * 60 + "\n"
                                
                                for archivo in archivos_data:
                                    # El formato es: (nombre, tipo, tamaño, fecha, ruta)
                                    nombre = archivo[0]
                                    tipo = archivo[1]
                                    tamaño = archivo[2]
                                    fecha = archivo[3]
                                    ruta = archivo[4]
                                    
                                    resultado += f"📄 {nombre}\n"
                                    resultado += f"   📋 Tipo: {tipo}\n"
                                    resultado += f"   📏 Tamaño: {tamaño} bytes\n"
                                    resultado += f"   📅 Fecha: {fecha}\n"
                                    if '5' in criterios:  # Mostrar ruta si se solicita
                                        resultado += f"   📁 Ruta: {ruta}\n"
                                    resultado += "-" * 40 + "\n"
                                
                                response_content = f'{resultado}'
                            else:
                                response_content = 'No se encontraron archivos con los criterios especificados'
                                
                        except Exception as e:
                            response_content = f'ERR|Error procesando datos: {str(e)}'
                    else:
                        response_content = f'ERR|Respuesta inesperada: {response_data_db.decode()}'
                        
                except Exception as e:
                    response_content = f'ERR|Error en búsqueda: {str(e)}'

            else:
                response_content = 'ERR|Comando no reconocido'

            # Enviar respuesta SIN "OK"
            full_response = service + response_content
            response_message = f'{len(full_response):05}'.encode() + full_response.encode()
            
            print(f'📤 Enviando respuesta: {response_message}')
            sock.sendall(response_message)

finally:
    print('closing socket')
    sock.close()
