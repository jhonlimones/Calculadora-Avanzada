# calculadora/core/export_utils.py

import pandas as pd

def export_to_csv(data, filename='export.csv'):
    """
    Exporta una lista de diccionarios a un archivo CSV.
    Convierte las columnas de fecha a formato legible.
    """
    if not data:
        print("No hay datos para exportar.")
        return

    df = pd.DataFrame(data)
    
    # Convertir las columnas de fecha a formato legible
    # Busca cualquier columna que contenga 'creado_en' en el nombre
    for col in df.columns:
        if 'creado_en' in col:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    df.to_csv(filename, index=False)
    print(f"Datos exportados correctamente a {filename}")

def export_to_excel(data, filename='export.xlsx'):
    """
    Exporta una lista de diccionarios a un archivo Excel.
    Convierte las columnas de fecha a formato legible.
    """
    if not data:
        print("No hay datos para exportar.")
        return

    df = pd.DataFrame(data)
    
    # Convertir las columnas de fecha a formato legible
    # Busca cualquier columna que contenga 'creado_en' en el nombre
    for col in df.columns:
        if 'creado_en' in col:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d %H:%M:%S')
    
    df.to_excel(filename, index=False)
    print(f"Datos exportados correctamente a {filename}")