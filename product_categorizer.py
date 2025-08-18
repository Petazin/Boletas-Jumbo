# -*- coding: utf-8 -*-
"""Módulo para la categorización de productos."""

def categorize_product(description):
    """Asigna una categoría a un producto basándose en palabras clave en su descripción.

    Args:
        description (str): La descripción del producto extraída de la boleta.

    Returns:
        str: La categoría asignada al producto. Devuelve "Otros" si no coincide con ninguna regla.
    """
    # Convertir la descripción a mayúsculas para hacer la búsqueda insensible a mayúsculas/minúsculas.
    description = description.upper()
    
    # El orden de las condiciones es importante para evitar falsos positivos.
    # Se debe ir de lo más específico a lo más general.

    # Mascotas
    if any(keyword in description for keyword in ['GATO', 'PERRO', 'WHISK', 'PEDIGREE', 'CAT CHOW', 'DOG CHOW', 'SNACK GATO']):
        return "Mascotas"

    # Higiene Personal
    if any(keyword in description for keyword in ['JABON', 'SHAMPOO', 'ACONDICIONADOR', 'PASTA DENTAL', 'COLGATE', 'PEPSODENT', 'DESODORANTE', 'REXONA', 'NIVEA', 'LADYSOFT', 'HIGIEN', 'ENJUAGUE BUCAL', 'PLAX', 'DEO', 'CEPILLO', 'ORAL', 'SENSODYNE', 'PROTEX', 'GILLETTE', 'SCHICK']):
        return "Higiene Personal"
    
    # Productos de Limpieza y Hogar
    if any(keyword in description for keyword in ['DETERGENTE', 'LAVALOZA', 'LIMPIADOR', 'CLORO', 'LYSOFORM', 'POETT', 'CIF', 'QUIX', 'PATO', 'RAID', 'VIRUTEX', 'ESPONJA', 'PANO', 'SUAVIZANTE', 'COMFORT', 'TOALLITA', 'DESINF', 'FILM', 'ALUSA', 'BOLSA', 'SERVILLET', 'PAPEL HIGIENICO', 'TOALLA', 'P.FAV', 'SCOTT', 'CONFORT', 'PACK ALUPLAST']):
        return "Productos de Limpieza y Hogar"

    # Carnes y Embutidos
    if any(keyword in description for keyword in ['CARNE', 'POLLO', 'PAVO', 'CERDO', 'VACUNO', 'HAMBURGUESA', 'SALCHI', 'JAMON', 'LONGANIZA', 'PECHUGA', 'TOCINO', 'VIENESA', 'PATE', 'LOMO', 'COSTILLAR', 'CHORIZO']):
        return "Carnes y Embutidos"

    # Pescados y Mariscos
    if any(keyword in description for keyword in ['PESCADO', 'MARISCO', 'ATUN', 'JUREL', 'SALMON']):
        return "Pescados y Mariscos"

    # Vinos y Licores
    if any(keyword in description for keyword in ['VINO', 'CERVEZA', 'PISCO', 'RON', 'WHISKY', 'GIN', 'VODKA', 'LICOR', 'ESPUMANTE', 'DRAMBUIE', 'CERV', 'PILS', 'SOUR', 'CHARD', 'MERLOT', 'CARMEN', 'CAB']):
        return "Vinos y Licores"

    # Lácteos y Huevos
    if any(keyword in description for keyword in ['LECHE', 'YOGUR', 'YOG', 'QUESO', 'MANTEQUILLA', 'CREMA', 'HUEVO', 'LACTEO', 'POSTRE', 'CHANDELLE', 'COLUN', 'GAUDA', 'CREAM CHEESE', 'RALLADO']):
        return "Lácteos y Huevos"

    # Pastas
    if any(keyword in description for keyword in ['PASTA', 'SPAGHETTI', 'TALLARIN', 'FIDEO', 'LASAÑA', 'CANUTO', 'ESPIRALES', 'CORBATA', 'MOSTACCIOLI', 'RIGATONI', 'QUIFAROS']):
        return "Pastas"

    # Aceites y Condimentos
    if any(keyword in description for keyword in ['ACEITE', 'SALSA', 'CONDIMENTO', 'MAYONESA', 'KETCHUP', 'MOSTAZA', 'VINAGRE', 'SAL', 'OREGANO', 'CURCUMA', 'HELLMANNS', 'MAY', 'SAZONADOR', 'PIMIENTA', 'COMINO', 'AJO', 'CEBOLLA EN POLVO', 'MERQUEN', 'ACETO', 'BALSAMICO']):
        return "Aceites y Condimentos"

    # Snacks y Dulces
    if any(keyword in description for keyword in ['SNACK', 'GALLETA', 'GALL', 'CHOCOLATE', 'CARAMELO', 'PAPAS FRITAS', 'PAPA', 'LAYS', 'MANI', 'OREO', 'CHIPS', 'MANJARATE', 'CRACKER', 'CRACKELET', 'PEPIN', 'ANTIPASTO', 'CHUCRUT', 'TABLA', 'DORITOS', 'RAMITAS', 'SUFLÉ', 'FRUTOS SECOS', 'ALMENDRAS', 'NUECES', 'PASAS']):
        return "Snacks y Dulces"

    # Panadería y Pastelería
    if any(keyword in description for keyword in ['PAN', 'MARRAQUETA', 'HALLULLA', 'TORTA', 'PASTEL', 'DONUT']):
        return "Panadería y Pastelería"

    # Cereales y Legumbres
    if any(keyword in description for keyword in ['CEREAL', 'ARROZ', 'QUINOA', 'AVENA', 'LENTEJA', 'GARBANZO', 'POROTO', 'HARINA', 'ARVEJAS']):
        return "Cereales y Legumbres"

    # Bebidas y Jugos
    if any(keyword in description for keyword in ['BEBIDA', 'JUGO', 'GASEOSA', 'AGUA', 'NECTAR', 'ZUMO', 'ENERGETICA', 'LIVEAN']):
        return "Bebidas y Jugos"

    # Congelados
    if any(keyword in description for keyword in ['CONGELADO', 'HELADO', 'PIZZA']):
        return "Congelados"
        
    # Frutas y Verduras
    if any(keyword in description for keyword in ['PLATANO', 'CHAMPINON', 'LECHUGA']):
        return "Frutas y Verduras"

    # Sopas y Caldos
    if any(keyword in description for keyword in ['SOPA']):
        return "Sopas y Caldos"

    # Té, Café y Azúcar
    if any(keyword in description for keyword in ['TE', 'CAFE', 'AZUCAR', 'ENDULZANTE', 'HIERBA', 'MATE', 'ALUSWEET', 'NESCAFE', 'STEVIA', 'SUCRALOSA', 'AGAVE', 'GOLD', 'DOLCE GUSTO']):
        return "Té, Café y Azúcar"
        
    # Si ninguna de las condiciones anteriores se cumple, se asigna la categoría por defecto.
    return "Otros"
