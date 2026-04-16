import streamlit as st
import datetime
import requests
import pandas as pd
import urllib3
import pytz

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

# --- LÓGICA DE CORRECCIÓN HORARIA INTELIGENTE ---
def corregir_hora_exacta(hora_str, fecha_obj):
    """Calcula el desfase (+1 o +2) para cualquier fecha (presente o futura)"""
    try:
        tz = pytz.timezone('Europe/Madrid')
        dt_consulta = datetime.datetime.combine(fecha_obj, datetime.time(12, 0))
        offset_segundos = tz.utcoffset(dt_consulta).total_seconds()
        horas_a_sumar = int(offset_segundos / 3600)
        
        h_api = datetime.datetime.strptime(hora_str, "%H:%M")
        h_corregida = h_api + datetime.timedelta(hours=horas_a_sumar)
        return h_corregida.strftime("%H:%M")
    except:
        return hora_str

# --- FUNCIONES DE APOYO ---
def obtener_flecha_dir(grados):
    if grados is None: return ""
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

# --- API CLIMA ---
@st.cache_data(ttl=900)
def obtener_clima_real(lat, lon, tipo):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=5).json()['current']
        estado, icono = codigo_clima_a_icono(res['weather_code'])
        datos = {
            "estado": estado, "icono": icono, "temp": res['temperature_2m'],
            "sensacion": res['apparent_temperature'], "lluvia": res['precipitation'],
            "viento": res['wind_speed_10m'], "rachas": res['wind_gusts_10m'],
            "dir_v": obtener_flecha_dir(res['wind_direction_10m']),
            "weather_code": res['weather_code']
        }
        if tipo == "mar":
            url_o = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,wave_direction&timezone=Europe%2FMadrid"
            res_o = requests.get(url_o, timeout=5).json()['current']
            datos.update({
                "olas_h": res_o.get('wave_height', 0),
                "olas_p": res_o.get('wave_period', 0),
                "olas_dir": obtener_flecha_dir(res_o.get('wave_direction', 0)),
                "agua": round(12.0 + (datetime.date.today().month * 0.8), 1)
            })
        return datos
    except: return None

# --- API MAREAS ---
@st.cache_data(ttl=3600)
def consultar_marea_ihm(id_puerto, fecha_obj):
    if not id_puerto: return None
    url = f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&date={fecha_obj.strftime('%Y%m%d')}"
    try:
        res = requests.get(url, timeout=10, verify=False)
        if res.status_code == 200:
            raw = res.json()
            marea_data = raw['mareas']['datos']['marea']
            eventos = list(marea_data.values()) if isinstance(marea_data, dict) else marea_data
            pleas, bajas = [], []
            for e in eventos:
                h_api = e.get('hora', '--:--')[:5]
                h_corregida = corregir_hora_exacta(h_api, fecha_obj)
                a = float(e.get('altura', 0))
                t = (e.get('tipo', '')).lower()
                if 'pleamar' in t: pleas.append({"h": h_corregida, "a": a})
                elif 'bajamar' in t: bajas.append({"h": h_corregida, "a": a})
            
            # --- CÁLCULO DE COEFICIENTE MEJORADO ---
            max_p = max([x['a'] for x in pleas]) if pleas else 0
            min_b = min([x['a'] for x in bajas]) if bajas else 0
            amplitud = max_p - min_b
            
            # Ajuste de escala (Base 3.7m para el Cantábrico)
            coef_calc = round((amplitud / 3.7) * 90)
            coef_final = max(20, min(120, coef_calc))
            
            return {"p": pleas, "b": bajas, "coef": coef_final}
    except: return None

# --- BARRA DE PROGRESO ---
def mostrar_progreso_marea(m_datos):
    tz = pytz.timezone('Europe/Madrid')
    now_local = datetime.datetime.now(tz).replace(tzinfo=None)
    
    events = []
    hoy = datetime.date.today()
    for m in m_datos['p']:
        events.append({"t": datetime.datetime.strptime(f"{hoy} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Plea"})
    for m in m_datos['b']:
        events.append({"t": datetime.datetime.strptime(f"{hoy} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Baja"})
    
    events.sort(key=lambda x: x['t'])
    
    for i in range(len(events)-1):
        if events[i]['t'] <= now_local <= events[i+1]['t']:
            progreso = (now_local - events[i]['t']).total_seconds() / (events[i+1]['t'] - events[i]['t']).total_seconds()
            mins = int((events[i+1]['t'] - now_local).total_seconds() / 60)
            estado = "IGOTZEN (Subiendo) ⬆️" if events[i+1]['tipo'] == "Plea" else "JAISTEN (Bajando) ⬇️"
            st.write(f"⏳ **Marea egoera:** {estado}")
            st.progress(progreso)
            st.caption(f"Hurrengo marea ({events[i+1]['tipo']}) {mins} minututan")
            return
    st.caption("Eguneko marea guztiak pasatu dira.")

#
