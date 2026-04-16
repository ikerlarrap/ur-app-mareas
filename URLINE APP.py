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
    """Detecta automáticamente si la fecha buscada es horario de verano (+2) o invierno (+1)"""
    try:
        tz = pytz.timezone('Europe/Madrid')
        h_api = datetime.datetime.strptime(hora_str, "%H:%M").time()
        dt_ingenuo = datetime.datetime.combine(fecha_obj, h_api)
        dt_localizado = tz.localize(dt_ingenuo)
        return dt_localizado.strftime("%H:%M")
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

# --- API MAREAS CON DST AUTOMÁTICO ---
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
                # AQUÍ SE APLICA LA MAGIA DEL CAMBIO DE HORA SEGÚN LA FECHA
                h_corregida = corregir_hora_exacta(h_api, fecha_obj)
                a = float(e.get('altura', 0))
                t = (e.get('tipo', '')).lower()
                if 'pleamar' in t: pleas.append({"h": h_corregida, "a": a})
                elif 'bajamar' in t: bajas.append({"h": h_corregida, "a": a})
            
            max_p = max([x['a'] for x in pleas]) if pleas else 0
            min_b = min([x['a'] for x in bajas]) if bajas else 0
            coef_calc = round(((max_p - min_b) / 4.5) * 100)
            return {"p": pleas, "b": bajas, "coef": coef_calc}
    except: return None

# --- BARRA DE PROGRESO CORREGIDA ---
def mostrar_progreso_marea(m_datos):
    tz = pytz.timezone('Europe/Madrid')
    now = datetime.datetime.now(tz).replace(tzinfo=None)
    events = []
    hoy = datetime.date.today()
    for m in m_datos['p']: events.append({"t": datetime.datetime.strptime(f"{hoy} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Plea"})
    for m in m_datos['b']: events.append({"t": datetime.datetime.strptime(f"{hoy} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Baja"})
    events.sort(key=lambda x: x['t'])
    
    for i in range(len(events)-1):
        if events[i]['t'] <= now <= events[i+1]['t']:
            progreso = (now - events[i]['t']).total_seconds() / (events[i+1]['t'] - events[i]['t']).total_seconds()
            mins = int((events[i+1]['t'] - now).total_seconds() / 60)
            estado = "IGOTZEN (Subiendo) ⬆️" if events[i+1]['tipo'] == "Plea" else "JAISTEN (Bajando) ⬇️"
            st.write(f"⏳ **Marea egoera:** {estado}")
            st.progress(progreso)
            st.caption(f"Hurrengo marea ({events[i+1]['tipo']}) {mins} minututan")
            return
    st.caption("Eguneko marea guztiak pasatu dira.")

# --- SIDEBAR ---
BASES = {
    "Ur Urdaibai": {"tipo": "mar", "lat": 43.396, "lon": -2.684, "id_ihm": "72"},
    "Ur Lekeitio": {"tipo": "mar", "lat": 43.364, "lon": -2.503, "id_ihm": "72"},
    "Mendexa Abentura Park": {"tipo": "monte", "lat": 43.361, "lon": -2.495, "id_ihm": None}
}

with st.sidebar:
    st.image("https://www.urdaibai.com/wp-content/uploads/2021/03/logo-ur-abentura.png", width=150)
    centro_sel = st.radio("Zentroa:", list(BASES.keys()))

info = BASES[centro_sel]
st.title(f"📍 {centro_sel}")
clima = obtener_clima_real(info['lat'], info['lon'], info['tipo'])

if clima:
    st.markdown(f"### {clima['icono']} {clima['estado']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tenperatura", f"{clima['temp']}°C")
    if info['tipo'] == "mar":
        c2.metric("Ura (Est.)", f"{clima['agua']}°C")
        c3.metric("Olatua", f"{clima['olas_h']}m", f"Norabidea: {clima['olas_dir']}")
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Haizea", f"{clima['viento']} km/h")
        cv2.metric("Raxak", f"{clima['rachas']} km/h", delta="⚠️" if clima['rachas']>25 else None)
        cv3.metric("Norabidea", clima['dir_v'])
        
        st.divider()
        m_hoy = consultar_marea_ihm(info['id_ihm'], datetime.date.today())
        if m_hoy:
            mostrar_progreso_marea(m_hoy)
            cp, cb = st.columns(2)
            with cp:
                st.info("⬆️ **Gora / Pleamar**")
                for p in m_hoy['p']: st.write(f"• **{p['h']}** ({p['a']}m)")
            with cb:
                st.warning("⬇️ **Behera / Bajamar**")
                for b in m_hoy['b']: st.write(f"• **{b['h']}** ({b['a']}m)")
            st.write(f"📊 **Koefiziente Kalkulatua:** {m_hoy['coef']}")
    else:
        c2.metric("Sentsazioa", f"{clima['sensacion']}°C")
        c3.metric("Euria", f"{clima['lluvia']} mm")
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Haizea", f"{clima['viento']} km/h")
        cv2.metric("Raxak", f"{clima['rachas']} km/h")
        cv3.metric("Norabidea", clima['dir_v'])
        st.divider()
        st.subheader("🌲 Mendexa Segurtasuna")
        m1, m2 = st.columns(2)
        riesgo = "ALTUA" if clima['weather_code'] >= 95 else "Baxua"
        m1.metric("Ekaitz Arriskua", riesgo, delta="⚠️ ITXITA" if riesgo == "ALTUA" else "OK")
        m2.metric("Max. Haizea", f"{clima['rachas']} km/h", delta="KONTUZ" if clima['rachas'] > 30 else "OK")

if info['tipo'] == "mar":
    with st.expander("🔍 Marea Bilatzailea (Ordu zuzendua / Hora corregida)"):
        f_bus = st.date_input("Data:", datetime.date.today())
        if st.button("Ikusi"):
            res = consultar_marea_ihm(info['id_ihm'], f_bus)
            if res:
                r1, r2 = st.columns(2)
                with r1:
                    st.info("⬆️ **Pleamar**")
                    for p in res['p']: st.write(f"• **{p['h']}** ({p['a']}m)")
                with r2:
                    st.warning("⬇️ **Bajamar**")
                    for b in res['b']: st.write(f"• **{b['h']}** ({b['a']}m)")
                st.write(f"📊 **Koefizientea:** {res['coef']}")

st.divider()
st.caption("UR Abentura PRO © 2026")
