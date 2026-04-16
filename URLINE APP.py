import streamlit as st
import datetime
import requests

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="UR Abentura - Operatibitatea", layout="wide", page_icon="⚓")

# Estilos visuales profesionales
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    [data-testid="stSidebar"] { background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

BASES = {
    "Ur Urdaibai": {"tipo": "mar", "lat": 43.396, "lon": -2.684},
    "Ur Lekeitio": {"tipo": "mar", "lat": 43.364, "lon": -2.503},
    "Mendexa Abentura Park": {"tipo": "monte", "lat": 43.361, "lon": -2.495}
}

# --- 2. MOTOR DE CLIMA (OPEN-METEO) ---
@st.cache_data(ttl=900)
def obtener_clima(lat, lon, tipo):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,wind_speed_10m,wind_gusts_10m&timezone=Europe%2FMadrid"
        res = requests.get(url, timeout=5).json()['current']
        
        datos = {"temp": res['temperature_2m'], "viento": res['wind_speed_10m'], "rachas": res['wind_gusts_10m']}
        
        if tipo == "mar":
            url_o = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height&timezone=Europe%2FMadrid"
            datos["olas"] = requests.get(url_o, timeout=5).json()['current']['wave_height']
        return datos
    except:
        return None

# --- 3. MOTOR DE MAREAS (API IHM - ARMADA) ---
@st.cache_data(ttl=3600)
def consultar_api_marea(fecha_obj):
    fecha_str = fecha_obj.strftime("%Y-%m-%d")
    url = f"https://ideihm.covam.es/api-ihm/getmarea?estacion=2&fecha={fecha_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://ideihm.covam.es/"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            datos = res.json()
            eventos = datos.get('mareas', [])
            pleas, bajas = [], []
            
            for e in eventos:
                h = (e.get('hora') or e.get('Hora') or "--:--")[:5]
                a = e.get('altura') or e.get('Altura') or "--"
                tipo = e.get('tipo') or e.get('Tipo')
                
                info = f"{h} ({a}m)"
                if tipo == 'Pleamar': pleas.append(info)
                elif tipo == 'Bajamar': bajas.append(info)
            
            return {
                "p1": pleas[0] if len(pleas) > 0 else "--:--",
                "p2": pleas[1] if len(pleas) > 1 else "--:--",
                "b1": bajas[0] if len(bajas) > 0 else "--:--",
                "b2": bajas[1] if len(bajas) > 1 else "--:--",
                "coef": datos.get('coeficiente') or datos.get('Coeficiente') or "--"
            }
    except:
        return {"error": "API konexio akatsa / Error de conexión con la Armada"}
    return {"error": "Daturik ez / Sin datos"}

# --- 4. INTERFAZ LATERAL ---
st.sidebar.title("⚓ UR Abentura")
centro_sel = st.sidebar.radio("Zentroa / Centro:", list(BASES.keys()))
st.sidebar.divider()
st.sidebar.info("Sarrera: API IHM Online")

# --- 5. CUERPO PRINCIPAL ---
info = BASES[centro_sel]
st.title(f"📍 {centro_sel}")

# Bloque de Clima
clima = obtener_clima(info['lat'], info['lon'], info['tipo'])
if clima:
    c1, c2, c3 = st.columns(3)
    c1.metric("Tenperatura", f"{clima['temp']}°C")
    c2.metric("Haizea", f"{clima['viento']} km/h", f"Raxak: {clima['rachas']}")
    if "olas" in clima:
        c3.metric("Olatua", f"{clima['olas']}m")

# Bloque de Mareas (solo Costa)
if info['tipo'] == "mar":
    st.divider()
    st.subheader(f"🌊 Gaurko Mareak ({datetime.date.today().strftime('%d/%m/%Y')})")
    
    with st.spinner("Datuak lortzen..."):
        m = consultar_api_marea(datetime.date.today())
        
        if "error" in m:
            st.error(m['error'])
        else:
            col_p, col_b = st.columns(2)
            with col_p:
                st.info(f"⬆️ **Pleamar**\n\n1️⃣ {m['p1']}\n\n2️⃣ {m['p2']}")
            with col_b:
                st.warning(f"⬇️ **Bajamar**\n\n1️⃣ {m['b1']}\n\n2️⃣ {m['b2']}")
            st.write(f"📊 **Koefizientea:** {m['coef']}")

    # Buscador de Mareas
    st.divider()
    st.subheader("🔍 Marea Bilatzailea")
    fecha_bus = st.date_input("Aukeratu data / Elegir fecha:", datetime.date.today())

    if st.button("Ikusi / Ver"):
        with st.spinner("APIa kontsultatzen..."):
            res = consultar_api_marea(fecha_bus)
            if "error" in res:
                st.error(res['error'])
            else:
                st.success(f"Datuak: {fecha_bus.strftime('%d/%m/%Y')}")
                cp, cb = st.columns(2)
                cp.info(f"⬆️ **Pleas:** {res['p1']} | {res['p2']}")
                cb.warning(f"⬇️ **Bajas:** {res['b1']} | {res['b2']}")
                st.write(f"📊 **Koef:** {res['coef']}")
else:
    st.info("Mendexa: Begiratu Lekeitio edo Urdaibai mareak ikusteko.")

st.divider()
st.caption("UR line © 2026 - API IHM Sistema")