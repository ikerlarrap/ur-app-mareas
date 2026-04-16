import streamlit as st
import datetime
import requests
import pandas as pd
import urllib3
import pytz

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="UR Abentura PRO", layout="wide", page_icon="⚓")

# --- CSS ADAPTATIVO Y MEJORAS UX MÓVIL ---
st.markdown("""
    <style>
    .stMetric { 
        background-color: var(--secondary-background-color); 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid var(--border-color); 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
    }
    .stProgress > div > div > div > div { background-color: #007bff; }
    
    /* Aviso visual para móviles indicando dónde está el menú */
    .mobile-menu-hint {
        display: none;
        background-color: #e2f0fb;
        color: #0056b3;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: bold;
        margin-bottom: 15px;
        border: 1px solid #b8daff;
    }
    
    /* Si la pantalla es pequeña (móvil), mostramos el aviso */
    @media (max-width: 768px) {
        .mobile-menu-hint {
            display: block;
        }
    }
    </style>
    """, unsafe_allow_html=True)

tz_madrid = pytz.timezone('Europe/Madrid')
now_local = datetime.datetime.now(tz_madrid)

# --- FUNCIONES ---
def corregir_hora_exacta(hora_str, fecha_obj):
    try:
        dt_consulta = datetime.datetime.combine(fecha_obj, datetime.time(12, 0))
        offset_segundos = tz_madrid.utcoffset(dt_consulta).total_seconds()
        horas_a_sumar = int(offset_segundos / 3600)
        h_api = datetime.datetime.strptime(hora_str, "%H:%M")
        h_corregida = h_api + datetime.timedelta(hours=horas_a_sumar)
        return h_corregida.strftime("%H:%M")
    except: return hora_str

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
    if codigo <= 1: return "☀️"
    elif codigo <= 3: return "⛅"
    elif codigo <= 48: return "🌫️"
    elif codigo <= 67 or codigo in [80, 81, 82]: return "🌧️"
    elif codigo >= 95: return "⛈️"
    return "❓"

def texto_clima(codigo):
    if codigo <= 1: return "Eguzkitsua / Soleado"
    elif codigo <= 3: return "Hodeitsu / Nublado"
    elif codigo <= 48: return "Lainoa / Niebla"
    elif codigo <= 67 or codigo in [80, 81, 82]: return "Euria / Lluvia"
    elif codigo >= 95: return "Ekaitza / Tormenta"
    return "Ezezaguna"

# --- API CLIMA ---
@st.cache_data(ttl=900)
def obtener_clima_completo(lat, lon, tipo):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m&hourly=temperature_2m,precipitation,wind_speed_10m,weather_code&daily=sunrise,sunset&timezone=Europe%2FMadrid"
    try:
        res = requests.get(url, timeout=15).json()
        curr = res['current']
        
        datos = {
            "estado": texto_clima(curr['weather_code']),
            "icono": codigo_clima_a_icono(curr['weather_code']),
            "temp": curr['temperature_2m'],
            "sensacion": curr['apparent_temperature'],
            "lluvia": curr['precipitation'],
            "viento": curr['wind_speed_10m'],
            "rachas": curr['wind_gusts_10m'],
            "dir_v": obtener_flecha_dir(curr['wind_direction_10m']),
            "weather_code": curr['weather_code'],
            "amanecer": res['daily']['sunrise'][0][-5:],
            "atardecer": res['daily']['sunset'][0][-5:],
            "hourly_times": res['hourly']['time'],
            "hourly_temps": res['hourly']['temperature_2m'],
            "hourly_rain": res['hourly']['precipitation'],
            "hourly_wind": res['hourly']['wind_speed_10m'],
            "hourly_icons": [codigo_clima_a_icono(c) for c in res['hourly']['weather_code']]
        }
        
        if tipo == "mar":
            try:
                url_o = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_period,wave_direction&timezone=Europe%2FMadrid"
                res_o = requests.get(url_o, timeout=10).json()
                if 'current' in res_o:
                    datos.update({
                        "olas_h": res_o['current'].get('wave_height', '--'),
                        "olas_p": res_o['current'].get('wave_period', '--'),
                        "olas_dir": obtener_flecha_dir(res_o['current'].get('wave_direction', None))
                    })
            except:
                datos.update({"olas_h": "--", "olas_p": "--", "olas_dir": ""})
            
            datos["agua"] = round(12.0 + (now_local.month * 0.8), 1)

        return datos
    except Exception as e: 
        return {"error": str(e)}

# --- API MAREAS ---
@st.cache_data(ttl=3600)
def consultar_marea_ihm(id_puerto, fecha_obj):
    if not id_puerto: return None
    url = f"http://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&date={fecha_obj.strftime('%Y%m%d')}"
    try:
        res = requests.get(url, timeout=15, verify=False)
        if res.status_code == 200:
            raw = res.json()
            if 'mareas' not in raw or 'datos' not in raw['mareas']:
                return {"error": "El servidor del IHM devolvió datos vacíos."}
                
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
            
            max_p = max([x['a'] for x in pleas]) if pleas else 0
            min_b = min([x['a'] for x in bajas]) if bajas else 0
            amplitud = max_p - min_b
            coef_calc = round((amplitud / 3.7) * 90)
            return {"p": pleas, "b": bajas, "coef": max(20, min(120, coef_calc))}
        else:
            return {"error": f"IHM bloqueado (Status {res.status_code})"}
    except Exception as e: 
        return {"error": f"Error de red: {str(e)}"}

# --- BARRA DE PROGRESO DE MAREAS ---
def mostrar_progreso_marea(m_datos):
    now_naive = now_local.replace(tzinfo=None)
    events = []
    hoy = datetime.date.today()
    for m in m_datos['p']: events.append({"t": datetime.datetime.strptime(f"{hoy} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Plea"})
    for m in m_datos['b']: events.append({"t": datetime.datetime.strptime(f"{hoy} {m['h']}", "%Y-%m-%d %H:%M"), "tipo": "Baja"})
    
    events.sort(key=lambda x: x['t'])
    for i in range(len(events)-1):
        if events[i]['t'] <= now_naive <= events[i+1]['t']:
            total = (events[i+1]['t'] - events[i]['t']).total_seconds()
            transcurrido = (now_naive - events[i]['t']).total_seconds()
            progreso = transcurrido / total
            mins = int((events[i+1]['t'] - now_naive).total_seconds() / 60)
            estado = "IGOTZEN (Subiendo) ⬆️" if events[i+1]['tipo'] == "Plea" else "JAISTEN (Bajando) ⬇️"
            st.write(f"⏳ **Marea egoera:** {estado}")
            st.progress(progreso)
            st.caption(f"Hurrengo marea ({events[i+1]['tipo']}) {mins} minututan")
            return
    st.caption("Eguneko marea guztiak pasatu dira.")

# --- SIDEBAR & DAYLIGHT TRACKER ---
BASES = {
    "Ur Urdaibai": {"tipo": "mar", "lat": 43.396, "lon": -2.684, "id_ihm": "72"},
    "Ur Lekeitio": {"tipo": "mar", "lat": 43.364, "lon": -2.503, "id_ihm": "72"},
    "Mendexa Abentura Park": {"tipo": "monte", "lat": 43.361, "lon": -2.495, "id_ihm": None}
}

with st.sidebar:
    try: st.image("logo.png", width=180)
    except: st.title("⚓ UR Abentura")
        
    centro_sel = st.radio("Zentroa:", list(BASES.keys()))
    info = BASES[centro_sel]
    clima = obtener_clima_completo(info['lat'], info['lon'], info['tipo'])
    
    st.divider()
    st.subheader("☀️ Argia / Luz")
    if clima and "error" not in clima:
        amanecer = clima['amanecer']
        atardecer = clima['atardecer']
        
        c1, c2 = st.columns(2)
        c1.write(f"🌅 **Egunsentia:**\n{amanecer}")
        c2.write(f"🌇 **Iluntzea:**\n{atardecer}")
        
        # --- CÁLCULO DE PROGRESO SOLAR ---
        hoy = datetime.date.today()
        t_amanecer = tz_madrid.localize(datetime.datetime.strptime(f"{hoy} {amanecer}", "%Y-%m-%d %H:%M"))
        t_atardecer = tz_madrid.localize(datetime.datetime.strptime(f"{hoy} {atardecer}", "%Y-%m-%d %H:%M"))
        
        if now_local < t_amanecer:
            st.info("🌙 Eguna ez da hasi / Noche")
            st.progress(0)
        elif now_local > t_atardecer:
            st.info("🌙 Eguna amaitu da / Noche")
            st.progress(100)
        else:
            total_luz = (t_atardecer - t_amanecer).total_seconds()
            transcurrido = (now_local - t_amanecer).total_seconds()
            progreso_solar = transcurrido / total_luz
            
            minutos_restantes = int((t_atardecer - now_local).total_seconds() / 60)
            horas_restantes = minutos_restantes // 60
            mins_rest = minutos_restantes % 60
            
            st.write(f"⏳ **Argi orduak / Luz restante:** {horas_restantes}h {mins_rest}m")
            st.progress(progreso_solar)
    else:
        st.warning("Ezin izan da eguzki-ordua kargatu.")
        
    st.divider()
    st.caption("UR line PRO © 2026")

# --- AVISO PARA MÓVILES (HTML INYECTADO) ---
st.markdown('<div class="mobile-menu-hint">👈 Sakatu goiko ezkerreko botoia zentroa aldatzeko / Toca arriba a la izquierda para cambiar de centro</div>', unsafe_allow_html=True)

# --- CABECERA PRINCIPAL ---
c_tit, c_fecha = st.columns([2, 1])
with c_tit:
    st.title(f"📍 {centro_sel}")
with c_fecha:
    st.info(f"📅 **{now_local.strftime('%Y-%m-%d')}** &nbsp;|&nbsp; ⏰ **{now_local.strftime('%H:%M')}**")

# 1. BLOQUE DE CLIMA
if clima and "error" not in clima:
    st.markdown(f"### {clima['icono']} {clima['estado']}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tenperatura", f"{clima['temp']}°C")
    
    if info['tipo'] == "mar":
        c2.metric("Ura (Est.)", f"{clima.get('agua', '--')}°C")
        c3.metric("Olatua", f"{clima.get('olas_h', '--')}m", f"{clima.get('olas_p','--')}s | {clima.get('olas_dir', '')}")
        
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Haizea", f"{clima['viento']} km/h")
        cv2.metric("Raxak", f"{clima['rachas']} km/h", delta="⚠️" if clima['rachas']>25 else None)
        cv3.metric("Norabidea", clima['dir_v'])
    else: # MENDEXA
        c2.metric("Sentsazioa", f"{clima['sensacion']}°C")
        c3.metric("Euria", f"{clima['lluvia']} mm")
        
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Haizea", f"{clima['viento']} km/h")
        cv2.metric("Raxak", f"{clima['rachas']} km/h")
        cv3.metric("Norabidea", clima['dir_v'])
        
        st.divider()
        st.subheader("🌲 Mendexa Segurtasuna")
        m1, m2 = st.columns(2)
        riesgo_t = "ALTUA" if clima['weather_code'] >= 95 else "Baxua"
        m1.metric("Ekaitz Arriskua", riesgo_t, delta="⚠️ ITXITA" if riesgo_t == "ALTUA" else "IREKITA")
        m2.metric("Max. Haizea", f"{clima['rachas']} km/h", delta="KONTUZ" if clima['rachas'] > 30 else "OK")

    # PREVISIÓN 12H (Solo horas futuras)
    st.divider()
    with st.expander("⏱️ Datoak orduz ordu / Previsión 12h"):
        hora_actual_str = now_local.strftime("%Y-%m-%dT%H:00")
        
        idx = 0
        for i, ht in enumerate(clima['hourly_times']):
            if ht >= hora_actual_str:
                idx = i
                break
                
        tiempos = [t[-5:] for t in clima['hourly_times'][idx:idx+12]]
        iconos = clima['hourly_icons'][idx:idx+12]
        temps = clima['hourly_temps'][idx:idx+12]
        vientos = clima['hourly_wind'][idx:idx+12]
        
        for t, ic, te, vi in zip(tiempos, iconos, temps, vientos):
            st.write(f"**{t}** | {ic} | 🌡️ {te}°C | 💨 {vi} km/h")
else:
    st.warning("⚠️ Ezin izan da eguraldia kargatu / No se ha podido cargar la meteorología.")

# 2. BLOQUE DE MAREAS (TOTALMENTE INDEPENDIENTE)
if info['tipo'] == "mar":
    st.divider()
    st.subheader(f"🌊 Gaurko Mareak")
    m_hoy = consultar_marea_ihm(info['id_ihm'], datetime.date.today())
    
    if m_hoy and "error" not in m_hoy:
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
        err_msg = m_hoy['error'] if m_hoy else "Error de conexión."
        st.error(f"⚠️ Arazoa mareak lortzean (IHM): {err_msg}")

    # BUSCADOR
    st.divider()
    with st.expander("🔍 Marea Bilatzailea (Ordu zuzendua)"):
        f_bus = st.date_input("Data:", datetime.date.today())
        if st.button("Ikusi"):
            res = consultar_marea_ihm(info['id_ihm'], f_bus)
            if res and "error" not in res:
                r1, r2 = st.columns(2)
                with r1:
                    st.info("⬆️ **Pleamar**")
                    for p in res['p']: st.write(f"• **{p['h']}** ({p['a']}m)")
                with r2:
                    st.warning("⬇️ **Bajamar**")
                    for b in res['b']: st.write(f"• **{b['h']}** ({b['a']}m)")
                st.write(f"📊 **Koefizientea:** {res['coef']}")
            else:
                st.error("Ezin izan dira datuak lortu.")

st.divider()
st.caption("URLINE © 2026 ")
