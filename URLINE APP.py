import streamlit as st
import datetime
import requests
import pandas as pd
import urllib3

# --- CONFIGURACIÓN DE SEGURIDAD Y PÁGINA ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="UR Abentura PRO", layout="wide", page_icon="⚓")

# Estilos CSS para un acabado profesional
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    .stMetric label { font-weight: bold; color: #495057; }
    </style>
    """, unsafe_allow_html=True)

# Configuración de Bases (ID 72 es Bermeo como referencia principal)
BASES = {
    "Ur Urdaibai": {"tipo": "mar", "lat": 43.396, "lon": -2.684, "id_ihm": "72"},
    "Ur Lekeitio": {"tipo": "mar", "lat": 43.364, "lon": -2.503, "id_ihm": "72"},
    "Mendexa Abentura Park": {"tipo": "monte", "lat": 43.361, "lon": -2.495, "id_ihm": None}
}

# --- FUNCIONES DE SOPORTE ---
def grados_a_direccion(grados):
    if grados is None: return "--"
    dirs = ['N (Ipar)', 'NE', 'E (Eki)', 'SE', 'S (Hego)', 'SW', 'W (Mend)', 'NW']
    return dirs[round(grados / 45) % 8]

def codigo_clima_a_icono(codigo):
    if codigo <= 1: return "Eguzkitsua / Soleado", "☀️"
    elif codigo <= 3: return "Hodeitsu / Nublado", "⛅"
    elif codigo <= 48: return "Lainoa / Niebla", "🌫️"
    elif codigo <= 67 or codigo in [80, 81, 82]: return "Euria / Lluvia", "🌧️"
    elif codigo >= 95: return "Ekaitza / Tormenta", "⛈️"
    return "Ezezaguna", "❓"

# --- 1. CLIMA Y OLAS (OPEN-METEO) ---
@st.cache_data(ttl=900)
def obtener_clima_real(lat, lon, tipo):
    url_clima = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=Europe%2FMadrid"
    try:
        req_clima = requests.get(url_clima, timeout=5).json()['current']
        estado, icono = codigo_clima_a_icono(req_clima['weather_code'])
        
        datos = {
            "estado": estado, "icono": icono, "temp": req_clima['temperature_2m'],
            "sensacion": req_clima['apparent_temperature'], "lluvia": req_clima['precipitation'],
            "viento": req_clima['wind_speed_10m'], "rachas": req_clima['wind_gusts_10m'],
            "dir": grados_a_direccion(req_clima['wind_direction_10m'])
        }
        if tipo == "mar":
            url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,wave_direction&timezone=Europe%2FMadrid"
            req_olas = requests.get(url_olas, timeout=5).json()['current']
            datos["olas_h"] = req_olas.get('wave_height', 0)
            datos["olas_p"] = req_olas.get('wave_period', 0)
            datos["agua"] = round(12.0 + (datetime.date.today().month * 0.8), 1) 
        return datos
    except:
        return None

# --- 2. MOTOR DE MAREAS (API IHM OFICIAL) ---
@st.cache_data(ttl=3600)
def consultar_marea_ihm(id_puerto, fecha_obj):
    if not id_puerto: return None
    # Formato oficial YYYYMMDD según documentación
    fecha_api = fecha_obj.strftime("%Y%m%d")
    url = f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&date={fecha_api}"
    
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    
    try:
        # verify=False para evitar bloqueos SSL en redes locales
        res = requests.get(url, headers=headers, timeout=10, verify=False)
        if res.status_code == 200:
            raw = res.json()
            # La API devuelve datos -> marea
            marea_data = raw['mareas']['datos']['marea']
            eventos = list(marea_data.values()) if isinstance(marea_data, dict) else marea_data
            
            pleas, bajas = [], []
            for e in eventos:
                h, a = e.get('hora', '--:--')[:5], e.get('altura', '--')
                tipo = e.get('tipo', '').lower()
                info = f"**{h}** ({a}m)"
                if 'pleamar' in tipo: pleas.append(info)
                elif 'bajamar' in tipo: bajas.append(info)
            
            return {
                "p1": pleas[0] if len(pleas) > 0 else "--",
                "p2": pleas[1] if len(pleas) > 1 else "--",
                "b1": bajas[0] if len(bajas) > 0 else "--",
                "b2": bajas[1] if len(bajas) > 1 else "--",
                "coef": raw['mareas'].get('coeficiente', '--'),
                "puerto": raw['mareas'].get('puerto', 'Bermeo')
            }
    except:
        return {"error": "API IHM ez dago erabilgarri / API IHM no disponible"}

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.urdaibai.com/wp-content/uploads/2021/03/logo-ur-abentura.png", width=150) # Logo genérico o local
    st.title("⚓ UR Abentura")
    centro_sel = st.radio("Zentroa / Centro:", list(BASES.keys()))
    st.divider()
    st.subheader("☀️ Argia / Luz")
    st.write("🌅 **Egunsentia:** 07:18")
    st.write("🌇 **Iluntzea:** 20:55")
    st.divider()
    st.caption("UR line PRO © 2026")

info = BASES[centro_sel]

# --- MAIN APP ---
st.title(f"📍 {centro_sel}")
clima = obtener_clima_real(info['lat'], info['lon'], info['tipo'])

if clima:
    st.markdown(f"### {clima['icono']} {clima['estado']}")
    
    # Fila 1: Temperaturas y Agua
    c1, c2, c3 = st.columns(3)
    c1.metric("Airearen Temp.", f"{clima['temp']}°C")
    if info['tipo'] == "mar":
        c2.metric("Uraren Temp. (Est.)", f"{clima['agua']}°C")
        c3.metric("Olatua / Ola", f"{clima['olas_h']}m", f"{clima['olas_p']}s")
    else:
        c2.metric("Sentsazioa", f"{clima['sensacion']}°C")
        c3.metric("Euria / Lluvia", f"{clima['lluvia']} mm")

    # Fila 2: Viento
    cv1, cv2, cv3 = st.columns(3)
    cv1.metric("Haizea / Viento", f"{clima['viento']} km/h")
    cv2.metric("Raxak / Rachas", f"{clima['rachas']} km/h", 
              delta="⚠️ Arriskua" if clima['rachas']>25 else None, delta_color="inverse")
    cv3.metric("Norabidea / Dir.", clima['dir'])

# --- SECCIÓN MAREAS ---
if info['tipo'] == "mar":
    st.divider()
    st.subheader(f"🌊 Gaurko Mareak / Mareas ({datetime.date.today().strftime('%d/%m/%Y')})")
    
    m_hoy = consultar_marea_ihm(info['id_ihm'], datetime.date.today())
    
    if m_hoy and "error" not in m_hoy:
        col_p, col_b = st.columns(2)
        with col_p:
            st.info("⬆️ **Gora / Pleamar**")
            st.markdown(f"1️⃣ {m_hoy['p1']}\n\n2️⃣ {m_hoy['p2']}")
        with col_b:
            st.warning("⬇️ **Behera / Bajamar**")
            st.markdown(f"1️⃣ {m_hoy['b1']}\n\n2️⃣ {m_hoy['b2']}")
        
        # Coeficiente y Corriente
        try:
            coef = int(m_hoy['coef'])
            msg_corriente = "⚠️ INDARTSUA / FUERTE" if coef > 80 else "Normala"
            st.write(f"📊 **Koefizientea:** {coef} | **Korrontea:** {msg_corriente}")
        except:
            st.write(f"📊 **Koefizientea:** {m_hoy['coef']}")
    else:
        st.error("⚠️ API konexio akatsa. Ezin izan dira mareak lortu.")

    # --- BUSCADOR ---
    st.divider()
    with st.expander("🔍 Marea Bilatzailea / Buscador de Mareas"):
        fecha_bus = st.date_input("Hautatu data:", datetime.date.today() + datetime.timedelta(days=1))
        if st.button("Bilatu / Consultar"):
            res = consultar_marea_ihm(info['id_ihm'], fecha_bus)
            if res and "error" not in res:
                st.success(f"Datuak lortuta: {fecha_bus}")
                b1, b2 = st.columns(2)
                b1.write(f"**Pleas:** {res['p1']} | {res['p2']}")
                b2.write(f"**Bajas:** {res['b1']} | {res['b2']}")
            else:
                st.error("Errorea datuak bilatzean.")

st.divider()
st.caption("UR Abentura Operatibitatea - Eskerrik asko zure lanagatik! ⚓")
