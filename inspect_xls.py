import pandas as pd
import sys

# Lee la ruta del archivo desde los argumentos de la lnea de comandos
file_path = sys.argv[1]

# Lee el archivo Excel sin asumir una fila de cabecera
df = pd.read_excel(file_path, header=None)

# Imprime el DataFrame completo como un string para ver toda la estructura
print(df.to_string())