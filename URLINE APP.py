import streamlit as st
import datetime
import requests
import urllib3
import os
import pandas as pd

# --- SEGURTASUN KONFIGURAZIOA ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="UR Abentura - API Konexio Finkoa", layout="wide", page_icon="⚓")

# Basen ID-ak (Aurkitu duzun 'id=72' Mundaka/Bermeo ingurukoa da)
BASES = {
    "Ur Urdaibai": {"lat": 43.396, "lon": -2.684, "tipo": "mar", "id_ihm": "72"},
    "Ur Lekeitio": {"lat": 43.364, "lon": -2.503, "tipo": "mar", "id_ihm": "75"}, 
    "Mendexa Abentura Park": {"lat": 43.361, "lon": -2.495, "tipo": "monte", "id_ihm": None}
}

# --- MAREA MOTORRA (SESIOAREKIN) ---
@st.cache_data(ttl=3600)
def consultar_api_marea(id_puerto, fecha_obj):
    if not id_puerto: return None
    
    fecha_str = fecha_obj.strftime("%Y-%m-%d")
    # Zuk aurkitutako URL-a aplikatuta
    url = f"https://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&fecha={fecha_str}"
    
    # Sesio bat sortzen dugu konexioa egonkorragoa izateko
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://ideihm.covam.es/ihm/mareas.html",
        "Origin": "https://ideihm.covam.es"
    }
    
    try:
        # Deia egiten dugu (verify=False ezinbestekoa da local-erako)
        res = session.get(url, headers=headers, timeout=15, verify=False)
        
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
                "coef": datos.get('coeficiente') or datos.get('Coeficiente') or "--",
                "origen": "📡 API (Online)"
            }
        else:
            # Zerbitzariak erantzun badu baina ez bada 200 (adibidez 403 edo 500)
            return {"error": f"Zerbitzariaren errorea: {res.status_code}"}
            
    except Exception as e:
        # API-ak huts egiten badu, CSV-ra jotzen dugu (Plan B)
        if os.path.exists('mareas_2026.csv'):
            try:
                df = pd.read_csv('mareas_2026.csv')
                df['fecha'] = pd.to_datetime(df['fecha']).dt.date
                fila = df[df['fecha'] == fecha_obj]
                if not fila.empty:
                    f = fila.iloc[0]
                    return {
                        "p1": f['p1'], "p2": f['p2'], "b1": f['b1'], "b2": f['b2'], 
                        "coef": f['coef'], "origen": "📁 CSV (Segurtasun kopia)"
                    }
            except: pass
        return {"error": f"Konexio akatsa: {str(e)}"}

# --- INTERFAZ NAGUSIA ---
with st.sidebar:
    st.title("⚓ UR Abentura")
    centro = st.radio("Zentroa:", list(BASES.keys()))
    st.divider()
    st.write(f"📅 Gaur: {datetime.date.today().strftime('%d/%m/%Y')}")

info = BASES[centro]
st.title(f"📍 {centro}")

if info['tipo'] == "mar":
    st.subheader("🌊 Mareen Egoera")
    
    # Karga prozesua
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
            st.error(f"⚠️ Ezin izan dira datuak kargatu: {m.get('error', 'Konexio ezezaguna')}")

    # Bilatzailea
    st.divider()
    st.subheader("🔍 Bilatzailea")
    fecha_bus = st.date_input("Data aukeratu:", datetime.date.today())
    if st.button("Ikusi"):
        res = consultar_api_marea(info['id_ihm'], fecha_bus)
        if res and "error" not in res:
            st.success(f"Datuak: {fecha_bus}")
            st.write(f"**Pleas:** {res['p1']} | {res['p2']}  \n**Bajas:** {res['b1']} | {res['b2']}  \n**Koef:** {res['coef']}")
        else:
            st.error("Errorea bilaketan.")
else:
    st.info("Mendexa: Mendi zentroa. Mareak ikusteko hautatu Lekeitio edo Urdaibai.")

st.divider()
st.caption("UR line © 2026 - API IHM Sistema Optimizatua")
