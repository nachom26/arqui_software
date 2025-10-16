import socket
import sqlite3

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
bus_addr = ('localhost', 5000)
sock.connect(bus_addr)
conn = sqlite3.connect('archivador.db')
cursor = conn.cursor()

cursor.execute('''
            CREATE TABLE IF NOT EXISTS carpeta(
                id_carpeta INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                propietario INTEGER REFERENCES usuarios(id_usuario),
                carpeta_padre INTEGER REFERENCES carpeta(id_carpeta)
            )''')

cursor.execute('''
            CREATE TABLE IF NOT EXISTS archivo(   
                id_archivo INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                tipo TEXT UNIQUE,
                tamaño INTEGER,
                fecha_subida DATETIME DEFAULT CURRENT_TIMESTAMP,
                propietario INTEGER REFERENCES usuarios(id_usuario),
                visibilidad TEXT,
                carpeta INTEGER REFERENCES carpeta(id_carpeta)
            )''')