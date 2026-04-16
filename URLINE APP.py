import streamlit as st
import requests
import datetime
import urllib3

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="UR Abentura - Bermeo API", layout="wide")

# Ambas bases apuntan a Bermeo (72)
BASES = {"Ur Urdaibai": "72", "Ur Lekeitio": "72"}

@st.cache_data(ttl=3600)
def llamar_api_ihm(id_puerto, fecha_obj):
    fecha_str = fecha_obj.strftime("%Y-%m-%d")
    # LA LLAMADA (Exactamente la URL que funciona)
    url = f"https://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&fecha={fecha_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0",
        "Referer": "https://ideihm.covam.es/ihm/mareas.html"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Servidor inaccesible (Status: {response.status_code})"}
    except Exception as e:
        return {"error": f"Fallo de red: {str(e)}"}

# --- INTERFAZ ---
st.title("⚓ UR Abentura - Operatibitatea")
centro = st.sidebar.radio("Hautatu Zentroa:", list(BASES.keys()))

st.header(f"🌊 Mareak: Bermeo (Referencia para {centro})")
datos_api = llamar_api_ihm(BASES[centro], datetime.date.today())

if "error" in datos_api:
    st.error(datos_api["error"])
    st.info("💡 Si falla la conexión, es por el firewall militar. Los datos están llegando bien al navegador pero el servidor bloquea a la App.")
else:
    try:
        # Extraemos la lista de mareas según tu estructura JSON
        # mareas -> datos -> marea
        marea_dict = datos_api['mareas']['datos']['marea']
        
        # Como vienen como "0", "1", "2"... los pasamos a una lista limpia
        eventos = list(marea_dict.values()) if isinstance(marea_dict, dict) else marea_dict

        # Mostrar resultados en columnas
        cols = st.columns(len(eventos))
        for i, m in enumerate(eventos):
            with cols[i]:
                es_plea = "pleamar" in m['tipo'].lower()
                st.metric(
                    label=f"{'⬆️' if es_plea else '⬇️'} {m['tipo'].upper()}",
                    value=m['hora'],
                    delta=f"{m['altura']}m",
                    delta_color="normal" if es_plea else "inverse"
                )
        
        st.success(f"Datu eguneratuak: {datos_api['mareas']['fecha']}")

    except Exception as e:
        st.warning("Egitura errorea datuak irakurtzean.")
        st.write(datos_api) # Para ver qué ha fallado en la lectura

st.divider()
st.caption("UR line © 2026 - Bermeo Ref. 72")
