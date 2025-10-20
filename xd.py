import sqlite3

db_path = 'archivador.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute(
                                'select * from archivo'
                            )

rows = cursor.fetchall()
for row in rows:
    print(row)
conn.close()
