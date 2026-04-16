import streamlit as st
import datetime
import requests
import urllib3
import os
import pandas as pd

# --- CONFIGURACIÓN DE SEGURIDAD ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="UR Abentura - API Directa", layout="wide", page_icon="⚓")

# --- BASES CON IDS DE LA API ---
# El ID 72 corresponde a la zona de Urdaibai/Mundaka en la nueva API
BASES = {
    "Ur Urdaibai": {"lat": 43.396, "lon": -2.684, "tipo": "mar", "id_ihm": "72"},
    "Ur Lekeitio": {"lat": 43.364, "lon": -2.503, "tipo": "mar", "id_ihm": "72"}, # Usamos 72 como referencia cercana
    "Mendexa Abentura Park": {"lat": 43.361, "lon": -2.495, "tipo": "monte", "id_ihm": None}
}

# --- MOTOR DE MAREAS (NUEVA API) ---
@st.cache_data(ttl=3600)
def consultar_api_marea(id_puerto, fecha_obj):
    if not id_puerto:
        return None
        
    fecha_str = fecha_obj.strftime("%Y-%m-%d")
    # Nueva estructura de URL que has encontrado
    url = f"https://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&fecha={fecha_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://ideihm.covam.es/ihm/mareas.html"
    }
    
    try:
        # Hacemos la llamada con los nuevos parámetros
        res = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if res.status_code == 200:
            datos = res.json()
            # La API devuelve una lista de mareas en el campo 'mareas'
            eventos = datos.get('mareas', [])
            
            pleas, bajas = [], []
            for e in eventos:
                # Extraemos hora y altura con limpieza de texto
                h = (e.get('hora') or e.get('Hora') or "--:--")[:5]
                a = e.get('altura') or e.get('Altura') or "--"
                tipo = e.get('tipo') or e.get('Tipo')
                
                info = f"{h} ({a}m)"
                if tipo == 'Pleamar': 
                    pleas.append(info)
                elif tipo == 'Bajamar': 
                    bajas.append(info)
            
            return {
                "origen": "📡 IHM API (Directa)",
                "p1": pleas[0] if len(pleas) > 0 else "--:--",
                "p2": pleas[1] if len(pleas) > 1 else "--:--",
                "b1": bajas[0] if len(bajas) > 0 else "--:--",
                "b2": bajas[1] if len(bajas) > 1 else "--:--",
                "coef": datos.get('coeficiente') or "--"
            }
    except Exception as e:
        # PLAN B: Si la API falla, intentamos leer el CSV si existe en GitHub
        if os.path.exists('mareas_2026.csv'):
            try:
                df = pd.read_csv('mareas_2026.csv')
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
                fila = df[df['fecha'] == fecha_obj]
                if not fila.empty:
                    f = fila.iloc[0]
                    return {
                        "origen": "📁 CSV Segurtasun kopia",
                        "p1": f['p1'], "p2": f['p2'], "b1": f['b1'], "b2": f['b2'], "coef": f['coef']
                    }
            except: pass
            
    return {"error": "Ezin izan da konexioa ezarri / Error de conexión"}

# --- INTERFAZ ---
st.sidebar.title("⚓ UR Abentura")
centro = st.sidebar.radio("Zentroa / Centro:", list(BASES.keys()))
info = BASES[centro]

st.title(f"📍 {centro}")

if info['tipo'] == "mar":
    st.subheader(f"🌊 Mareak / Mareas ({datetime.date.today().strftime('%d/%m/%Y')})")
    
    m = consultar_api_marea(info['id_ihm'], datetime.date.today())
    
    if m and "error" not in m:
        st.caption(f"Iturria: {m['origen']}")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"⬆️ **Pleamar**\n\n1️⃣ {m['p1']}\n\n2️⃣ {m['p2']}")
        with col2:
            st.warning(f"⬇️ **Bajamar**\n\n1️⃣ {m['b1']}\n\n2️⃣ {m['b2']}")
        st.write(f"📊 **Koefizientea:** {m['coef']}")
    else:
        st.error("Datuak ezin dira kargatu. Begiratu konexioa.")

    # Buscador
    st.divider()
    st.subheader("🔍 Marea Bilatzailea")
    f_bus = st.date_input("Data:", datetime.date.today())
    if st.button("Bilatu / Buscar"):
        res = consultar_api_marea(info['id_ihm'], f_bus)
        if res and "error" not in res:
            st.success(f"Datuak: {f_bus}")
            st.write(f"**Pleas:** {res['p1']} | {res['p2']}  \n**Bajas:** {res['b1']} | {res['b2']}")
        else:
            st.error("Akatsa datuak bilatzean.")
else:
    st.info("Mendexa: Centro de montaña. Consulta Lekeitio o Urdaibai para mareas.")

st.divider()
st.caption("UR line © 2026 - API IHM Sistema Berria")
