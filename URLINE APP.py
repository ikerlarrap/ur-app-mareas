import streamlit as st
import requests
import datetime
import urllib3

# --- CONFIGURACIÓN DE SEGURIDAD ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="UR Abentura - IHM Oficial", layout="wide")

# ID 72 es Bermeo (el que hemos comprobado que funciona)
ID_BERMEO = "72"

@st.cache_data(ttl=3600)
def obtener_mareas_ihm(id_puerto, fecha_obj):
    # Ajuste según documentación: formato YYYYMMDD
    fecha_api = fecha_obj.strftime("%Y%m%d")
    
    # Construcción exacta de la URL según tu texto:
    # http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id=72&format=json&date=20260416
    url = f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&date={fecha_api}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0",
        "Accept": "application/json"
    }

    try:
        # Probamos con la URL oficial
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return response.json()
        return {"error": f"API Error {response.status_code}"}
    except Exception as e:
        return {"error": f"Fallo de conexión: {str(e)}"}

# --- INTERFAZ ---
st.title("⚓ UR Abentura - Operatibitatea")
st.write("Datos oficiales del Instituto Hidrográfico de la Marina")

# Selector de fecha para el buscador
fecha_consulta = st.date_input("Aukeratu data / Selecciona fecha:", datetime.date.today())

if st.button("Ikusi Mareak / Ver Mareas"):
    with st.spinner("Cargando datos oficiales..."):
        datos = obtener_mareas_ihm(ID_BERMEO, fecha_consulta)
        
        if "error" in datos:
            st.error(datos["error"])
            st.info("Si persiste el error de conexión, es probable que el servidor de la Armada bloquee el acceso desde la nube (Streamlit).")
        else:
            try:
                # Acceso a la estructura: mareas -> datos -> marea
                lista_mareas = datos['mareas']['datos']['marea']
                
                # Convertimos a lista si viene como diccionario indexado
                eventos = list(lista_mareas.values()) if isinstance(lista_mareas, dict) else lista_mareas
                
                st.subheader(f"Portua: {datos['mareas']['puerto']} - Eguna: {fecha_consulta}")
                
                cols = st.columns(len(eventos))
                for i, m in enumerate(eventos):
                    with cols[i]:
                        # Clasificamos por tipo
                        tipo = m['tipo'].upper()
                        color = "normal" if "PLEAMAR" in tipo else "inverse"
                        icono = "⬆️" if "PLEAMAR" in tipo else "⬇️"
                        
                        st.metric(
                            label=f"{icono} {tipo}",
                            value=m['hora'],
                            delta=f"{m['altura']}m",
                            delta_color=color
                        )
                
                st.caption(f"Copyright: {datos['mareas']['copyright']}")

            except Exception as e:
                st.error("Error al procesar el formato de los datos.")
                st.write("Estructura recibida:", datos)

st.divider()
st.caption("UR line © 2026 - API IHM Standard Compliance")
