import os
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        logging.info(f"Created directory: {path}")

def move_file(source, destination):
    try:
        ensure_dir(os.path.dirname(destination))
        shutil.move(source, destination)
        logging.info(f"Moved: {source} to {destination}")
    except Exception as e:
        logging.error(f"Error moving {source} to {destination}: {e}")

# Base directories
BASE_DIR = r'c:\Users\Petazo\Desktop\Boletas Jumbo'
DESCARTAS_BANCO = os.path.join(BASE_DIR, 'descargas', 'Banco')

# Find all files in procesados subfolders and move them one level up
for root, dirs, files in os.walk(DESCARTAS_BANCO):
    if os.path.basename(root) == 'procesados':
        parent_dir = os.path.dirname(root)
        for file in files:
            source_path = os.path.join(root, file)
            destination_path = os.path.join(parent_dir, file)
            move_file(source_path, destination_path)