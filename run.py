import subprocess
import os

# Obtiene la ruta del directorio actual
current_dir = os.path.dirname(os.path.abspath(__file__)) + "/componentes"
print(f"Directorio actual: {current_dir}")

# Lista todos los archivos en el directorio actual
files = os.listdir(current_dir)
print(f"Archivos en el directorio: {files}")

# Filtra solo los archivos .py
services = [file for file in files if file.endswith('.py') and file.startswith('serv_')]
print(f"Servicios encontrados: {services}")

# Ejecuta cada servicio en una nueva consola
for service in services:
    service_path = os.path.abspath(os.path.join(current_dir, service))
    if os.name == 'nt':  # Para Windows
        command = f'start "" cmd /k "python \"{service_path}\""'
        print(f"Ejecutando comando en Windows: {command}")
        subprocess.Popen(command, shell=True)
    else:  # Para Linux/macOS
        command = f'gnome-terminal -- bash -c "python3 \\"{service_path}\\"; exec bash"'
        print(f"Ejecutando comando en Linux/macOS: {command}")
        subprocess.Popen(command, shell=True)

print("Todos los servicios se están ejecutando en consolas separadas.")