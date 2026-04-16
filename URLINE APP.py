import streamlit as st
import datetime
import requests
import pandas as pd
import urllib3
import time

# --- CONFIGURACIÓN DE SEGURIDAD Y PÁGINA ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="UR Abentura PRO", layout="wide", page_icon="⚓")

# Estilos CSS
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #e9ecef; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dee2e6; }
    .stAlert { border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

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
            "dir": grados_a_direccion(req_clima['wind_direction_10m']),
            "weather_code": req_clima['weather_code']
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

# --- MAREAS ---
@st.cache_data(ttl=3600)
def consultar_marea_ihm(id_puerto, fecha_obj):
    if not id_puerto: return None
    fecha_api = fecha_obj.strftime("%Y%m%d")
    url = f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&date={fecha_api}"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10, verify=False)
        if res.status_code == 200:
            raw = res.json()
            marea_data = raw['mareas']['datos']['marea']
            eventos = list(marea_data.values()) if isinstance(marea_data, dict) else marea_data
            
            pleas, bajas = [], []
            for e in eventos:
                h, a = e.get('hora', '--:--')[:5], e.get('altura', '--')
                tipo = e.get('tipo', '').lower()
                if 'pleamar' in tipo: pleas.append({"h": h, "a": a})
                elif 'bajamar' in tipo: bajas.append({"h": h, "a": a})
            
            return {
                "p": pleas, "b": bajas,
                "coef": raw['mareas'].get('coeficiente', '--')
            }
    except:
        return None

# --- LÓGICA DE BARRA DE PROGRESO ---
def mostrar_progreso_marea(m_datos):
    now = datetime.datetime.now()
    all_times = []
    for m in m_datos['p'] + m_datos['b']:
        t = datetime.datetime.strptime(f"{now.date()} {m['h']}", "%Y-%m-%d %H:%M")
        all_times.append(t)
    
    all_times.sort()
    
    # Encontrar entre qué mareas estamos
    for i in range(len(all_times)-1):
        if all_times[i] <= now <= all_times[i+1]:
            diff_total = (all_times[i+1] - all_times[i]).total_seconds()
            diff_now = (now - all_times[i]).total_seconds()
            progreso = diff_now / diff_total
            mins_faltan = int((all_times[i+1] - now).total_seconds() / 60)
            
            st.write(f"⏳ **Marea egoera:** Hurrengo aldaketa {mins_faltan} minututan")
            st.progress(progreso)
            return
    st.caption("Eguneko marea guztiak pasatu dira edo ez dira oraindik hasi.")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.urdaibai.com/wp-content/uploads/2021/03/logo-ur-abentura.png", width=150)
    st.title("⚓ UR Abentura")
    centro_sel = st.radio("Zentroa / Centro:", list(BASES.keys()))
    st.divider()
    st.subheader("☀️ Argia / Luz")
    st.write("🌅 **Egunsentia:** 07:18")
    st.write("🌇 **Iluntzea:** 20:55")
    st.caption("UR line PRO © 2026")

info = BASES[centro_sel]
st.title(f"📍 {centro_sel}")
clima = obtener_clima_real(info['lat'], info['lon'], info['tipo'])

if clima:
    st.markdown(f"### {clima['icono']} {clima['estado']}")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Airearen Temp.", f"{clima['temp']}°C")
    
    if info['tipo'] == "mar":
        c2.metric("Uraren Temp. (Est.)", f"{clima['agua']}°C")
        c3.metric("Olatua / Ola", f"{clima['olas_h']}m", f"{clima['olas_p']}s")
        
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Haizea / Viento", f"{clima['viento']} km/h")
        cv2.metric("Raxak / Rachas", f"{clima['rachas']} km/h", 
                  delta="⚠️ Arriskua" if clima['rachas']>25 else None, delta_color="inverse")
        cv3.metric("Norabidea / Dir.", clima['dir'])
        
        # Mareas Hoy
        st.divider()
        st.subheader(f"🌊 Gaurko Mareak ({datetime.date.today().strftime('%d/%m/%Y')})")
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
        
    else: # MENDEXA SPECIAL
        c2.metric("Hezetasuna / Hum.", f"{clima['sensacion']}°C", "Sentsazioa")
        c3.metric("Euria / Lluvia", f"{clima['lluvia']} mm")
        
        st.divider()
        st.subheader("🌲 Mendexa Segurtasun Indizea")
        m1, m2 = st.columns(2)
        
        # Parámetro extra: Riesgo de Tormenta Eléctrica
        riesgo_tormenta = "ALTUA / ALTO" if clima['weather_code'] >= 95 else "Baxua / Bajo"
        m1.metric("Ekaitz Arriskua", riesgo_tormenta, delta="ITXITA" if riesgo_tormenta == "ALTUA / ALTO" else "IREKITA", delta_color="inverse")
        
        # Parámetro extra: Viento en altura (Rachas)
        m2.metric("Max. Haizea (Zuhaitzak)", f"{clima['rachas']} km/h", delta="⚠️ KONTUZ" if clima['rachas'] > 30 else "OK")
        
        if clima['rachas'] > 35:
            st.error("❗ **ADI:** Haize bolada gogorrak. Tirolinak eta goiko jolasak ixtea gomendatzen da.")
        elif clima['weather_code'] >= 95:
            st.error("⛈️ **EKATZA:** Segurtasun protokoloa aktibatu. Parkea hustu.")

# --- BUSCADOR BONITO ---
if info['tipo'] == "mar":
    st.divider()
    with st.expander("🔍 Marea Bilatzailea / Buscador de Mareas"):
        fecha_bus = st.date_input("Hautatu data:", datetime.date.today() + datetime.timedelta(days=1))
        if st.button("Bilatu / Consultar"):
            res = consultar_marea_ihm(info['id_ihm'], fecha_bus)
            if res:
                st.success(f"Datuak lortuta: {fecha_bus.strftime('%d/%m/%Y')}")
                # Formato idéntico al principal
                res_p, res_b = st.columns(2)
                with res_p:
                    st.info("⬆️ **Gora / Pleamar**")
                    for p in res['p']: st.write(f"• **{p['h']}** ({p['a']}m)")
                with res_b:
                    st.warning("⬇️ **Behera / Bajamar**")
                    for b in res['b']: st.write(f"• **{b['h']}** ({b['a']}m)")
                st.write(f"📊 **Koefizientea:** {res['coef']}")
            else:
                st.error("Errorea datuak bilatzean.")

st.divider()
st.caption("UR Abentura Operatibitatea - Eskerrik asko zure lanagatik! ⚓")
