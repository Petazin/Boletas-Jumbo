# -*- coding: utf-8 -*-
"""
Este script se encarga de poblar la base de datos con un conjunto inicial y
estandarizado de categorías, subcategorías y reglas de mapeo para la 
clasificación de transacciones financieras.

Versión 3: Corregido error de SQL (nombre de columna incorrecto).

Funcionalidad:
1.  Define una estructura jerárquica de categorías (principales y subcategorías).
2.  Establece reglas basadas en palabras clave para asociar descripciones de 
    transacciones a una subcategoría específica.
3.  Limpia las tablas relacionadas (`mapeo_clasificacion_transacciones`, 
    `subcategorias`, `categorias_principales`) para asegurar una carga limpia.
4.  Inserta los datos definidos en la base de datos.

Uso:
- Ejecutar este script directamente desde la línea de comandos para poblar o 
  resetear las categorías en la base de datos.
- `python src/utils/populate_categories.py`
"""

import sys
import os
import logging

# Configuración del logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Añadir el directorio raíz del proyecto al sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from db.database_utils import db_connection

# ==============================================================================
# DEFINICIÓN DE LA ESTRUCTURA DE CATEGORÍAS Y REGLAS
# ==============================================================================

CATEGORIAS_ESTRUCTURA = {
    "Ingresos": {
        "Sueldo y Salarios": ["NEOGISTICA"],
        "Ingresos por Inversiones": ["INTERESES GANADOS", "DIVIDENDO"],
        "Devoluciones": ["DEVOLUCION COMPRA", "DEV IMPUESTO"],
        "Otros Ingresos": []
    },
    "Gastos Fijos": {
        "Vivienda": ["ARRIENDO", "HIPOTECA", "DIVIDENDO", "CONDOMINIO", "PAC Credito Hipotecario"],
        "Cuentas Básicas": ["AGUAS ANDINAS", "ENEL", "METROGAS", "CHILQUINTA", "SOLEGAS"],
        "Telecomunicaciones": ["MOVISTAR", "ENTEL", "CLARO", "VTR", "MUNDO"],
        "Seguros": ["SEGURO", "PRIMA", "BCI SEGUROS", "CONSORCIO", "SURA", "Cobro Seguros Desgravamen", "CARGO SEGURO", "PRIMA SEGURO DESGRAVAMEN", "SEG CESANTIA", "SEG DESGRAVAMEN", "PAC CONSORCIO"],
        "Educación": ["COLEGIO", "UNIVERSIDAD", "MENSUALIDAD", "U V M", "SOC. EDUCACIONAL"],
        "Suscripciones": ["NETFLIX", "SPOTIFY", "PRIME VIDEO", "HBO", "DISNEY+", "CANVA", "PlayStation Network", "STEAMGAMES.COM", "SIE*PLAYSTATIONNETW"]
    },
    "Gastos Variables": {
        "Alimentación y Supermercado": ["JUMBO", "LIDER", "TOTTUS", "UNIMARC", "PAN", "VERDURAS", "STA ISABEL", "HIPER LIDER", "MAS PAN", "PETINES MARKET", "MINIMARKET", "SAN LORENZO", "JUMBO ONECLICK", "VERDULERIA", "LID EXPRES", "FRUTOS SECOS", "DON CLAUDIO", "PANADERIA", "MARSELLA PANAD", "LAYOYITA", "MASPAN", "LAGRANJA", "ELMERCAD", "FRUTASMY", "LATINITA"],
        "Restaurantes y Comida Rápida": ["RESTAURANT", "STARBUCKS", "MCDONALDS", "BURGER KING", "PEDIDOSYA", "RAPPI", "IL CAPO DI TUTTI", "EL GRAN MANDARIN", "PLATON MARINA", "dondeNeron", "QUECHUA", "UBER EATS"],
        "Transporte": ["UBER", "DIDI", "CABIFY", "METRO", "BIP!", "COPEC", "SHELL", "PETROBRAS", "EFE VALPARAISO", "MERVAL", "MUEVO COPEC"],
        "Peajes y Estacionamientos": ["AUTOPISTA", "EST. MALL"],
        "Salud y Bienestar": ["FARMACIA", "CRUZ VERDE", "AHUMADA", "SALCOBRAND", "CLINICA", "REDSALUD", "INTEGRAMEDICA", "CLINICA LOS CARRERA", "FASA", "ECOFARMACIAS"],
        "Grandes Tiendas y Malls": ["FALABELLA", "RIPLEY", "PARIS", "MALL PLAZA", "MALL MARINA", "HYM MARINA ARAUCO"],
        "Compras Online": ["MERCADOLIBRE", "ALIEXPRESS", "MERPAGO", "SumUp", "EBANX", "PAYU", "VENTIPAY.COM", "TUU*"],
        "Hogar y Construcción": ["EASY", "SODIMAC"],
        "Ocio y Entretenimiento": ["CINE", "CINEHOYTS", "CINEMARK", "TEATRO", "CONCIERTO", "NINTENDO"],
        "Ropa y Accesorios": ["ZARA", "H&M", "ISIMONSE", "DOCKERSC", "BMBASICS", "ANKERINN", "PARA ELLOS", "DBS"],
        "Mascotas": ["HOUSE PET"],
        "Libros y Art. Oficina": ["LIBRERIA ANTARTICA", "BOOKS AND BITS"],
        "Otros Comercios": ["DMA SPORT", "ROCKET TCG GAME", "BONY TO PILLIN", "COMERCIAL KAROL", "FULLERTON", "coldcenter", "COMERCIAL LINXI"],
        "Viajes y Vacaciones": ["LATAM", "SKY AIRLINE", "BOOKING", "DESPEGAR", "HOTEL"]
    },
    "Financiero y Obligaciones": {
        "Pagos de Tarjetas": ["PAGO TARJETA", "PAGO TC", "Pago Pesos TEF", "Pago Dolar TEF"],
        "Pagos de Créditos": ["PAGO CREDITO", "PAGO CONSUMO", "PAC Credito Hipotecario", "PAGO AUTOM. LINEA DE CREDITO", "AMORTIZACION A LINEA DE CREDITO"],
        "Impuestos": ["TESORERIA GENERAL", "IMPUESTO", "IVA", "RENTA", "CARGO POR COBRO DE IVA", "IMPUESTO DL 3475", "PAGO EN SII.CL", "PERMISO DE CIRCULACION"],
        "Comisiones y Cargos Bancarios": ["COMISION", "MANTENIMIENTO", "CARGO FIJO", "Comision Mantencion", "COMISION ADMIN. MENSUAL", "COMISION COMPRA INTERNACIONAL", "INTERESES ROTATIVOS", "CARGO INTERES LC CTA CTE", "INTERESES LINEA DE CREDITO", "SERVICIO ADMINISTRACION"],
        "Giros y Avances": ["GIRO CAJERO AUTOMATICO"],
        "Inversiones": ["FONDO MUTUO", "DEPOSITO A PLAZO", "ACCIONES"]
    },
    "Transferencias": {
        "Transferencia Saliente": ["TRANSFERENCIA A TERCEROS", "TRASPASO A:"],
        "Transferencia Entrante": ["TRANSFERENCIA DE TERCEROS", "TRASPASO DE:"]
    },
    "Otros y No Clasificados": {
        "Otros Gastos": [],
        "Ajustes y Reversas": ["REVERSA", "AJUSTE", "DEVOLUCION", "DEVOLUCION INTERESES"],
        "Cargos No Identificados": []
    }
}

def populate_categories():
    """
    Limpia y puebla las tablas de categorías, subcategorías y mapeo.
    """
    try:
        with db_connection() as conn:
            cursor = conn.cursor()
            logging.info("Conexión a la base de datos establecida.")

            # --- Limpieza de tablas ---
            logging.info("Limpiando tablas de clasificación existentes...")
            cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
            cursor.execute("TRUNCATE TABLE mapeo_clasificacion_transacciones;")
            cursor.execute("TRUNCATE TABLE subcategorias;")
            cursor.execute("TRUNCATE TABLE categorias_principales;")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            logging.info("Tablas limpiadas exitosamente.")

            # --- Inserción de datos ---
            logging.info("Insertando nuevas categorías, subcategorías y reglas...")
            
            # Insertar categorías principales y obtener sus IDs
            cat_ids = {}
            for cat_nombre in CATEGORIAS_ESTRUCTURA.keys():
                # Determinar el tipo de transacción
                tipo_trans = 'Gasto' # Valor por defecto
                if cat_nombre == 'Ingresos':
                    tipo_trans = 'Ingreso'
                elif cat_nombre == 'Transferencias':
                    tipo_trans = 'Transferencia'
                
                # CORRECCIÓN: Usar 'nombre_categoria_principal' y añadir 'tipo_transaccion'
                sql_cat = "INSERT INTO categorias_principales (nombre_categoria_principal, tipo_transaccion) VALUES (%s, %s)"
                cursor.execute(sql_cat, (cat_nombre, tipo_trans))
                cat_ids[cat_nombre] = cursor.lastrowid

            # Insertar subcategorías y reglas de mapeo
            for cat_nombre, subcategorias in CATEGORIAS_ESTRUCTURA.items():
                cat_id = cat_ids[cat_nombre]
                for sub_nombre, palabras_clave in subcategorias.items():
                    cursor.execute("INSERT INTO subcategorias (categoria_principal_id, nombre_subcategoria) VALUES (%s, %s)", (cat_id, sub_nombre))
                    sub_id = cursor.lastrowid
                    
                    for palabra in palabras_clave:
                        sql_map = "INSERT INTO mapeo_clasificacion_transacciones (palabra_clave, subcategoria_id) VALUES (%s, %s)"
                        cursor.execute(sql_map, (palabra, sub_id))

            conn.commit()
            logging.info("Población de categorías completada exitosamente.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante la población de categorías: {e}")
        logging.info("La transacción fue revertida automáticamente por el error.")

if __name__ == "__main__":
    populate_categories()
