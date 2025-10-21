import sqlite3

conn = sqlite3.connect('sistema_archivos.db')
cursor = conn.cursor()

cursor.execute(''' select * from usuarios ''')
print(cursor.fetchall())