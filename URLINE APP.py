import streamlit as st
import datetime
import requests
import urllib3
import os
import pandas as pd

# --- SEGURTASUN KONFIGURAZIOA ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="UR Abentura - API Konexio Finkoa", layout="wide", page_icon="⚓")

# Basen ID-ak (Zuk bidalitako 'id=72' Bermeo/Mundaka ingurukoa da)
BASES = {
    "Ur Urdaibai": {"lat": 43.396, "lon": -2.684, "tipo": "mar", "id_ihm": "72"},
    "Ur Lekeitio": {"lat": 43.364, "lon": -2.503, "tipo": "mar", "id_ihm": "75"}, 
    "Mendexa Abentura Park": {"lat": 43.361, "lon": -2.495, "tipo": "monte", "id_ihm": None}
}

# --- MAREA MOTORRA (ZUK EMANDAKO EGITURARA EGOKITUTA) ---
@st.cache_data(ttl=3600)
def consultar_api_marea(id_puerto, fecha_obj):
    if not id_puerto: return None
    
    fecha_str = fecha_obj.strftime("%Y-%m-%d")
    # Zuk aurkitutako URL zehatza parametro guztiekin
    url = f"https://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&fecha={fecha_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://ideihm.covam.es/ihm/mareas.html"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if res.status_code == 200:
            raw_data = res.json()
            
            # Zuk bidalitako egitura: datos -> marea (zerrenda edo hiztegia)
            # Kasu batzuetan 'datos' barruan 'marea' dago, besteetan zuzenean 'mareas'
            eventos = []
            if 'datos' in raw_data and 'marea' in raw_data['datos']:
                eventos = raw_data['datos']['marea']
            elif 'mareas' in raw_data:
                eventos = raw_data['mareas']
            
            # Zerrenda bada (normalena), indizeekin edo gabe kudeatu
            if isinstance(eventos, dict):
                eventos = list(eventos.values())

            pleas, bajas = [], []
            for e in eventos:
                h = (e.get('hora') or "--:--")[:5]
                a = e.get('altura') or "--"
                tipo = (e.get('tipo') or "").lower()
                
                info = f"{h} ({a}m)"
                if 'pleamar' in tipo:
                    pleas.append(info)
                elif 'bajamar' in tipo:
                    bajas.append(info)
            
            return {
                "p1": pleas[0] if len(pleas) > 0 else "--:--",
                "p2": pleas[1] if len(pleas) > 1 else "--:--",
                "b1": bajas[0] if len(bajas) > 0 else "--:--",
                "b2": bajas[1] if len(bajas) > 1 else "--:--",
                "coef": raw_data.get('coeficiente') or "--",
                "origen": "📡 IHM API (Online)"
            }
        else:
            return {"error": f"Zerbitzariaren errorea: {res.status_code}"}
            
    except Exception as e:
        # PLAN B: API-ak huts egiten badu, CSV-ra jotzen dugu
        if os.path.exists('mareas_2026.csv'):
            try:
                df = pd.read_csv('mareas_2026.csv')
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
                fila = df[df['fecha'] == fecha_obj]
                if not fila.empty:
                    f = fila.iloc[0]
                    return {
                        "p1": f['p1'], "p2": f['p2'], "b1": f['b1'], "b2": f['b2'], 
                        "coef": f['coef'], "origen": "📁 CSV Segurtasun kopia"
                    }
            except: pass
        return {"error": "Konexio akatsa. APIa ez dago erabilgarri."}

# --- INTERFAZ NAGUSIA ---
st.sidebar.title("⚓ UR Abentura")
centro = st.sidebar.radio("Zentroa:", list(BASES.keys()))
st.sidebar.divider()
st.sidebar.write(f"📅 Gaur: {datetime.date.today().strftime('%d/%m/%Y')}")

info = BASES[centro]
st.title(f"📍 {centro}")

if info['tipo'] == "mar":
    st.subheader("🌊 Mareen Egoera")
    
    with st.spinner("Datuak lortzen..."):
        m = consultar_api_marea(info['id_ihm'], datetime.date.today())
        
        if m and "error" not in m:
            st.caption(f"Iturria: {m['origen']}")
            c1, c2 = st.columns(2)
            with c1:
                st.info(f"⬆️ **Gora / Pleamar**\n\n1: {m['p1']}\n\n2: {m['p2']}")
            with c2:
                st.warning(f"⬇️ **Behera / Bajamar**\n\n1: {m['b1']}\n\n2: {m['b2']}")
            st.write(f"📊 **Koefizientea:** {m['coef']}")
        else:
            st.error(f"⚠️ Ezin izan dira datuak kargatu: {m.get('error')}")

    # Bilatzailea
    st.divider()
    st.subheader("🔍 Marea Bilatzailea")
    fecha_bus = st.date_input("Data aukeratu:", datetime.date.today())
    if st.button("Bilatu"):
        res = consultar_api_marea(info['id_ihm'], fecha_bus)
        if res and "error" not in res:
            st.success(f"Datuak: {fecha_bus.strftime('%d/%m/%Y')}")
            col1, col2 = st.columns(2)
            col1.info(f"**Gora:** {res['p1']} | {res['p2']}")
            col2.warning(f"**Behera:** {res['b1']} | {res['b2']}")
            st.write(f"**Koef:** {res['coef']}")
        else:
            st.error("Errorea bilaketan.")
else:
    st.info("Mendexa: Mendi zentroa. Mareak ikusteko hautatu Lekeitio edo Urdaibai.")

st.divider()
st.caption("UR line © 2026 - API IHM Sistema Berria")
