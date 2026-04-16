import streamlit as st
import datetime
import requests
import pandas as pd
import urllib3

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="UR Abentura PRO", layout="wide", page_icon="⚓")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    </style>
    """, unsafe_allow_html=True)

BASES = {
    "Ur Urdaibai": {"tipo": "mar", "lat": 43.396, "lon": -2.684, "id_ihm": "72"},
    "Ur Lekeitio": {"tipo": "mar", "lat": 43.364, "lon": -2.503, "id_ihm": "72"},
    "Mendexa Abentura Park": {"tipo": "monte", "lat": 43.361, "lon": -2.495, "id_ihm": None}
}

# --- FUNCIONES DE SOPORTE ---
def obtener_flecha_dir(grados):
    if grados is None: return ""
    # Flechas según dirección
    if 337.5 <= grados or grados < 22.5: return "⬇️ (N)"
    if 22.5 <= grados < 67.5: return "↙️ (NE)"
    if 67.5 <= grados < 112.5: return "⬅️ (E)"
    if 112.5 <= grados < 157.5: return "↖️ (SE)"
    if 157.5 <= grados < 202.5: return "⬆️ (S)"
    if 202.5 <= grados < 247.5: return "↗️ (SW)"
    if 247.5 <= grados < 292.5: return "➡️ (W)"
    if 292.5 <= grados < 337.5: return "↘️ (NW)"
    return ""

def codigo_clima_a_icono(codigo):
    if codigo <= 1: return "Eguzkitsua / Soleado", "☀️"
    elif codigo <= 3: return "Hodeitsu / Nublado", "⛅"
    elif codigo <= 48: return "Lainoa / Niebla", "🌫️"
    elif codigo <= 67 or codigo in [80, 81, 82]: return "Euria / Lluvia", "🌧️"
    elif codigo >= 95: return "Ekaitza / Tormenta", "⛈️"
    return "Ezezaguna", "❓"

# --- CLIMA ---
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
            "dir_v": obtener_flecha_dir(req_clima['wind_direction_10m']),
            "weather_code": req_clima['weather_code']
        }
        if tipo == "mar":
            url_olas = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,wave_direction&timezone=Europe%2FMadrid"
            req_olas = requests.get(url_olas, timeout=5).json()['current']
            datos["olas_h"] = req_olas.get('wave_height', 0)
            datos["olas_p"] = req_olas.get('wave_period', 0)
            datos["olas_dir"] = obtener_flecha_dir(req_olas.get('wave_direction', 0))
            datos["agua"] = round(12.0 + (datetime.date.today().month * 0.8), 1) 
        return datos
    except:
        return None

# --- MAREAS ---
@st.cache_data(ttl=3600)
def consultar_marea_ihm(id_puerto, fecha_obj):
    if not id_puerto: return None
    fecha_api = fecha_obj.strftime("%Y%m%d")
    url = f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&date={fecha_api}"
    try:
        res = requests.get(url, timeout=10, verify=False)
        if res.status_code == 200:
            raw = res.json()
            marea_data = raw['mareas']['datos']['marea']
            eventos = list(marea_data.values()) if isinstance(marea_data, dict) else marea_data
            
            pleas, bajas = [], []
            for e in eventos:
                h, a = e.get('hora', '--:--')[:5], float(e.get('altura', 0))
                tipo = e.get('tipo', '').lower()
                if 'pleamar' in tipo: pleas.append({"h": h, "a": a})
                elif 'bajamar' in tipo: bajas.append({"h": h, "a": a})
            
            # Cálculo automático de coeficiente aproximado (Diff entre la mayor plea y menor baja)
            max_p = max([x['a'] for x in pleas]) if pleas else 0
            min_b = min([x['a'] for x in bajas]) if bajas else 0
            diff = max_p - min_b
            coef_calc = round((diff / 4.5) * 100) # 4.5m es marea viva extrema en el Cantábrico

            return {"p": pleas, "b": bajas, "coef": coef_calc}
    except:
        return None

# --- BARRA DE PROGRESO ---
def mostrar_progreso_marea(m_datos):
    now = datetime.datetime.now()
    all_events = []
    for m in m_datos['p']: all_events.append({"t": datetime.datetime.strptime(f"{now.date()} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Plea"})
    for m in m_datos['b']: all_events.append({"t": datetime.datetime.strptime(f"{now.date()} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Baja"})
    
    all_events.sort(key=lambda x: x['t'])
    
    for i in range(len(all_events)-1):
        if all_events[i]['t'] <= now <= all_events[i+1]['t']:
            diff_total = (all_events[i+1]['t'] - all_events[i]['t']).total_seconds()
            diff_now = (now - all_events[i]['t']).total_seconds()
            progreso = diff_now / diff_total
            mins_faltan = int((all_events[i+1]['t'] - now).total_seconds() / 60)
            
            # Determinar si sube o baja
            estado = "IGOTZEN (Subiendo) ⬆️" if all_events[i+1]['tipo'] == "Plea" else "JAISTEN (Bajando) ⬇️"
            
            st.write(f"⏳ **Marea egoera:** {estado}")
            st.progress(progreso)
            st.caption(f"Hurrengo marea ({all_events[i+1]['tipo']}) {mins_faltan} minututan")
            return
    st.caption("Marea guztiak pasatu dira.")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.urdaibai.com/wp-content/uploads/2021/03/logo-ur-abentura.png", width=150)
    st.title("⚓ UR Abentura")
    centro_sel
