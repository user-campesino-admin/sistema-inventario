import streamlit as st
import pandas as pd
from database import SessionLocal, RegistroInventario

st.set_page_config(page_title="Sistema de Inventario", layout="wide")

st.title("Gestión de Inventario")

# Opciones de navegación
menu = st.sidebar.radio("Opciones", ["Cargar TXT", "Cruce con Excel", "Gestionar Historial"])

# --- 1. Lógica de Carga de TXT MÚLTIPLES (OPTIMIZADA PARA VELOCIDAD) ---
if menu == "Cargar TXT":
    st.header("Cargar archivos de inventario (.txt)")
    
    uploaded_files = st.file_uploader("Selecciona los archivos .txt", type=['txt'], accept_multiple_files=True)
    ciudad = st.text_input("Ciudad de origen")
    
    if uploaded_files and ciudad and st.button("Procesar"):
        columnas = ['tipificacion', 'serie', 'estado_a', 'hub', 'regional', 'nodo', 'ciudad', 'fecha', 'estado_actual_rr', 'cuenta', 'estado_anterior', 'ot', 'cod_sap', 'descripcion', 'contraccion', 'hora']
        
        with SessionLocal() as session:
            try:
                total_registros = 0
                for file in uploaded_files:
                    # Leer archivo
                    df = pd.read_csv(file, header=None, names=columnas, sep='\t', dtype=str, encoding='latin-1')
                    
                    # MAGIA DE VELOCIDAD 1: Agregar variables a toda la columna de un solo golpe
                    df['ciudad_origen'] = ciudad
                    
                    # PENDIENTE AÑADIDO: Capturar el nombre del archivo para poder borrarlo individualmente después
                    df['nombre_archivo'] = file.name 
                    
                    # MAGIA DE VELOCIDAD 2: Convertir a diccionario e insertar en bloque (Bulk Insert)
                    # Esto evita evaluar fila por fila y manda el paquete completo a SQLite
                    session.bulk_insert_mappings(RegistroInventario, df.to_dict(orient='records'))
                    
                    total_registros += len(df)
                
                # Guardar cambios
                session.commit()
                st.success(f"¡Carga Turbo exitosa! Se guardaron {total_registros} registros provenientes de {len(uploaded_files)} archivo(s) .txt.")
            
            except Exception as e:
                session.rollback()
                st.error(f"Hubo un error al guardar: {e}")

# --- 2. Lógica de Cruce con Excel ---
elif menu == "Cruce con Excel":
    st.header("Cruce de datos contra base central")
    uploaded_excel = st.file_uploader("Selecciona tu archivo Excel de control", type=['xlsx'])
    
    if uploaded_excel and st.button("Ejecutar Cruce"):
        df_usuario = pd.read_excel(uploaded_excel)
        df_usuario.columns = df_usuario.columns.str.strip()
        
        columna_serie_usuario = next((col for col in df_usuario.columns if col.upper() == 'SERIE'), None)
        
        if not columna_serie_usuario:
            st.error("No se encontró ninguna columna de 'SERIE' en tu archivo Excel.")
        else:
            with SessionLocal() as session:
                df_central = pd.read_sql(session.query(RegistroInventario).statement, session.bind)
            
            # Conservar solo la trazabilidad más reciente por cada 'serie'
            df_central = df_central.sort_values('id').drop_duplicates(subset=['serie'], keep='last')
            
            resultado = pd.merge(df_usuario, df_central, left_on=columna_serie_usuario, right_on='serie', how='inner')
            
            st.write(f"Resultados del cruce (Coincidencias encontradas: {len(resultado)}):")
            st.dataframe(resultado)
            
            csv = resultado.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar reporte", csv, "resultado_cruce.csv", "text/csv")

# --- 3. Lógica de Gestión de Historial ---
elif menu == "Gestionar Historial":
    st.header("Gestión y Limpieza del Historial")
    
    with SessionLocal() as session:
        total_registros = session.query(RegistroInventario).count()
        st.info(f"Total de registros actualmente en la base de datos: {total_registros}")
        
        if total_registros > 0:
            
            # PENDIENTE AÑADIDO 1: Vista previa de los datos acumulados
            st.subheader("📊 Vista previa de la base de datos")
            df_historico = pd.read_sql(session.query(RegistroInventario).statement, session.bind)
            st.dataframe(df_historico)
            
            st.markdown("---")
            
            # PENDIENTE AÑADIDO 2: Eliminación por TXT específico
            st.subheader("1. Eliminar TXT específico")
            try:
                archivos_bd = session.query(RegistroInventario.nombre_archivo).distinct().all()
                lista_archivos = [a[0] for a in archivos_bd if a[0] is not None]
                
                archivo_a_borrar = st.selectbox("Selecciona el archivo TXT exacto que deseas eliminar:", [""] + lista_archivos)
                
                if archivo_a_borrar and st.button(f"Eliminar registros de '{archivo_a_borrar}'"):
                    borrados = session.query(RegistroInventario).filter_by(nombre_archivo=archivo_a_borrar).delete()
                    session.commit()
                    st.success(f"Se eliminaron {borrados} registros del archivo '{archivo_a_borrar}'.")
                    st.rerun()
            except Exception as e:
                st.warning("⚠️ Para poder borrar por archivo, recuerda que debes agregar `nombre_archivo = Column(String)` en tu archivo `database.py` y borrar tu archivo actual `inventario.db`.")
            
            st.markdown("---")
            
            # MANTENIDO: Eliminar por lote (Ciudad de Origen)
            st.subheader("2. Eliminar por lote (Ciudad de Origen)")
            
            ciudades_bd = session.query(RegistroInventario.ciudad_origen).distinct().all()
            lista_ciudades = [c[0] for c in ciudades_bd if c[0]]
            
            ciudad_a_borrar = st.selectbox("Selecciona la ciudad que deseas eliminar:", [""] + lista_ciudades)
            
            if ciudad_a_borrar and st.button(f"Eliminar registros de {ciudad_a_borrar}"):
                borrados = session.query(RegistroInventario).filter_by(ciudad_origen=ciudad_a_borrar).delete()
                session.commit()
                st.success(f"Se eliminaron {borrados} registros correspondientes a la ciudad '{ciudad_a_borrar}'.")
                st.rerun()
            
            st.markdown("---")
            
            # MANTENIDO: Vaciar todo
            st.subheader("3. Empezar desde cero")
            st.warning("⚠️ Esta acción borrará absolutamente todo el historial almacenado.")
            
            if st.button("Vaciar toda la base de datos"):
                borrados = session.query(RegistroInventario).delete()
                session.commit()
                st.success(f"Base de datos reiniciada. Se eliminaron {borrados} registros en total.")
                st.rerun()
        else:
            st.write("La base de datos está vacía. No hay información para mostrar ni eliminar.")