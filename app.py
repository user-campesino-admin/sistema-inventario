import os
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Intentar obtener la URL desde los secretos de Streamlit Cloud, si no, usar entorno local
try:
    DATABASE_URL = st.secrets["DATABASE_URL"]
except:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///inventario.db")

engine = create_engine(DATABASE_URL)
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

# Crear las tablas en Supabase automáticamente si no existen
Base.metadata.create_all(bind=engine)