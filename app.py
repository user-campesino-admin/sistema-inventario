import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

st.set_page_config(page_title="Sistema de Inventario", layout="wide")

# --- CONEXIÓN A BASE DE DATOS ---
try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///inventario.db")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "supabase.com" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RegistroInventario(Base):
    __tablename__ = "registros_inventario"

    id = Column(Integer, primary_key=True, index=True)
    tipificacion = Column(String)
    serie = Column(String)
    estado_a = Column(String)
    hub = Column(String)
    regional = Column(String)
    nodo = Column(String)
    ciudad = Column(String)
    fecha = Column(String)
    estado_actual_rr = Column(String)
    cuenta = Column(String)
    estado_anterior = Column(String)
    ot = Column(String)
    cod_sap = Column(String)
    descripcion = Column(String)
    contraccion = Column(String)
    hora = Column(String)
    ciudad_origen = Column(String)
    nombre_archivo = Column(String)

try:
    Base.metadata.create_all(bind=engine)
except Exception as db_error:
    st.warning(f"Nota de conexión a base de datos: {db_error}")

# --- APLICACIÓN STREAMLIT ---
st.title("Gestión de Inventario")

menu = st.sidebar.radio("Opciones", ["Cargar TXT", "Cruce con Excel", "Gestionar Historial"], key="menu_principal_nav")

# --- 1. CARGA DE TXT ---
if menu == "Cargar TXT":
    st.header("Cargar archivos de inventario (.txt)")
    
    uploaded_files = st.file_uploader("Selecciona los archivos .txt", type=['txt'], accept_multiple_files=True, key="uploader_txt_principal")
    ciudad = st.text_input("Ciudad de origen", key="input_ciudad_origen")
    
    if uploaded_files and ciudad and st.button("Procesar", key="btn_procesar_txt"):
        columnas = ['tipificacion', 'serie', 'estado_a', 'hub', 'regional', 'nodo', 'ciudad', 'fecha', 'estado_actual_rr', 'cuenta', 'estado_anterior', 'ot', 'cod_sap', 'descripcion', 'contraccion', 'hora']
        
        with SessionLocal() as session:
            try:
                total_registros = 0
                for file in uploaded_files:
                    df = pd.read_csv(file, header=None, names=columnas, sep='\t', dtype=str, encoding='latin-1', low_memory=False)
                    
                    df['serie'] = df['serie'].astype(str).str.strip()
                    df['ciudad_origen'] = ciudad
                    df['nombre_archivo'] = file.name 
                    
                    session.bulk_insert_mappings(RegistroInventario, df.to_dict(orient='records'))
                    total_registros += len(df)
                
                session.commit()
                st.success(f"¡Carga exitosa! Se guardaron {total_registros} registros de {len(uploaded_files)} archivo(s).")
            
            except Exception as e:
                session.rollback()
                st.error(f"Hubo un error al guardar: {e}")

# --- 2. CRUCE CON EXCEL ---
elif menu == "Cruce con Excel":
    st.header("Cruce de datos contra base central")
    uploaded_excel = st.file_uploader("Selecciona tu archivo Excel de control", type=['xlsx'], key="uploader_excel_cruce")
    
    if uploaded_excel and st.button("Ejecutar Cruce", key="btn_ejecutar_cruce"):
        df_usuario = pd.read_excel(uploaded_excel)
        df_usuario.columns = df_usuario.columns.str.strip()
        
        columna_serie_usuario = next((col for col in df_usuario.columns if col.upper() == 'SERIE'), None)
        
        if not columna_serie_usuario:
            st.error("No se encontró ninguna columna de 'SERIE' en tu archivo Excel.")
        else:
            df_usuario[columna_serie_usuario] = df_usuario[columna_serie_usuario].astype(str).str.strip()

            with SessionLocal() as session:
                df_central = pd.read_sql(session.query(RegistroInventario).statement, session.bind)
            
            df_central['serie'] = df_central['serie'].astype(str).str.strip()
            df_central = df_central.sort_values('id').drop_duplicates(subset=['serie'], keep='last')
            
            resultado = pd.merge(df_usuario, df_central, left_on=columna_serie_usuario, right_on='serie', how='inner')
            
            st.write(f"Resultados del cruce (Coincidencias encontradas: {len(resultado)}):")
            st.dataframe(resultado)
            
            csv = resultado.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar reporte", csv, "resultado_cruce.csv", "text/csv", key="download_btn_cruce")

# --- 3. GESTIÓN DE HISTORIAL ---
elif menu == "Gestionar Historial":
    st.header("Gestión y Limpieza del Historial")
    
    with SessionLocal() as session:
        try:
            total_registros = session.query(RegistroInventario).count()
        except:
            total_registros = 0
            
        st.info(f"Total de registros actualmente en la base de datos: {total_registros}")
        
        if total_registros > 0:
            st.subheader("📊 Vista previa de la base de datos")
            df_historico = pd.read_sql(session.query(RegistroInventario).statement, session.bind)
            st.dataframe(df_historico)
            
            st.markdown("---")
            st.subheader("1. Eliminar TXT específico")
            try:
                archivos_bd = session.query(RegistroInventario.nombre_archivo).distinct().all()
                lista_archivos = [a[0] for a in archivos_bd if a[0] is not None]
                
                archivo_a_borrar = st.selectbox("Selecciona el archivo TXT exacto que deseas eliminar:", [""] + lista_archivos, key="select_archivo_borrar")
                
                if archivo_a_borrar and st.button(f"Eliminar registros de '{archivo_a_borrar}'", key="btn_borrar_archivo_especifico"):
                    borrados = session.query(RegistroInventario).filter_by(nombre_archivo=archivo_a_borrar).delete()
                    session.commit()
                    st.success(f"Se eliminaron {borrados} registros del archivo '{archivo_a_borrar}'.")
                    st.rerun()
            except Exception as e:
                st.warning(f"Error: {e}")
            
            st.markdown("---")
            st.subheader("2. Eliminar por lote (Ciudad de Origen)")
            ciudades_bd = session.query(RegistroInventario.ciudad_origen).distinct().all()
            lista_ciudades = [c[0] for c in ciudades_bd if c[0]]
            
            ciudad_a_borrar = st.selectbox("Selecciona la ciudad que deseas eliminar:", [""] + lista_ciudades, key="select_ciudad_borrar")
            
            if ciudad_a_borrar and st.button(f"Eliminar registros de {ciudad_a_borrar}", key="btn_borrar_ciudad_especifica"):
                borrados = session.query(RegistroInventario).filter_by(ciudad_origen=ciudad_a_borrar).delete()
                session.commit()
                st.success(f"Se eliminaron {borrados} registros de '{ciudad_a_borrar}'.")
                st.rerun()
            
            st.markdown("---")
            st.subheader("3. Empezar desde cero")
            st.warning("⚠️ Esta acción borrará absolutamente todo el historial almacenado.")
            
            if st.button("Vaciar toda la base de datos", key="btn_vaciar_toda_la_db"):
                borrados = session.query(RegistroInventario).delete()
                session.commit()
                st.success(f"Base de datos reiniciada. Se eliminaron {borrados} registros.")
                st.rerun()
        else:
            st.write("La base de datos está vacía o se está reconectando. No hay información para mostrar.")