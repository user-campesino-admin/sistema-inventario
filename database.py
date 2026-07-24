from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Configuramos una base de datos local llamada inventario.db
engine = create_engine('sqlite:///inventario.db', echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class RegistroInventario(Base):
    __tablename__ = 'registros_inventario'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tipificacion = Column(String(100))
    serie = Column(String(100), index=True) # Columna clave para cruces
    estado_a = Column(String(50))
    hub = Column(String(50))
    regional = Column(String(50))
    nodo = Column(String(50), index=True)
    ciudad = Column(String(50))
    fecha = Column(String(50))
    estado_actual_rr = Column(String(50))
    cuenta = Column(String(50))
    estado_anterior = Column(String(50))
    ot = Column(String(50))
    cod_sap = Column(String(50))
    descripcion = Column(Text)
    contraccion = Column(String(50))
    hora = Column(String(50))
    
    # Metadatos para saber quién y cuándo lo cargó
    ciudad_origen = Column(String(50))
    fecha_ingreso = Column(DateTime, default=datetime.utcnow)

def inicializar_bd():
    Base.metadata.create_all(engine)
    print("Base de datos y tablas creadas exitosamente.")

if __name__ == "__main__":
    inicializar_bd()