import streamlit as st
import datetime
import requests
import urllib3
import os

# Segurtasun abisuak kendu
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="UR Abentura - Bermeo API", layout="wide", page_icon="⚓")

# BI ZENTROAK BERMEOREKIN (ID 72)
BASES = {
    "Ur Urdaibai (Bermeo)": {"lat": 43.396, "lon": -2.684, "tipo": "mar", "id_ihm": "72"},
    "Ur Lekeitio (Bermeo)": {"lat": 43.364, "lon": -2.503, "tipo": "mar", "id_ihm": "72"},
    "Mendexa Abentura Park": {"lat": 43.361, "lon": -2.495, "tipo": "monte", "id_ihm": None}
}

@st.cache_data(ttl=3600)
def consultar_api_marea(id_puerto, fecha_obj):
    if not id_puerto: return None
    
    fecha_str = fecha_obj.strftime("%Y-%m-%d")
    # Zuk pasatako URL formatua
    url = f"https://ideihm.covam.es/api-ihm/getmarea?request=gettide&id={id_puerto}&format=json&fecha={fecha_str}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Referer": "https://ideihm.covam.es/ihm/mareas.html"
    }
    
    try:
        # Konexio saiakera (verify=False ezinbestekoa da)
        res = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if res.status_code == 200:
            raw_data = res.json()
            
            # ZUK BIDALITAKO EGITURA: mareas -> datos -> marea
            # Kontuz: Batzuetan egitura 'mareas' barruan dago, besteetan zuzenean.
            try:
                if 'mareas' in raw_data:
                    eventos = raw_data['mareas']['datos']['marea']
                else:
                    eventos = raw_data['datos']['marea']
            except KeyError:
                return {"error": "Datuen egitura aldatu da. Jarri harremanetan teknikariarekin."}

            pleas, bajas = [], []
            for e in eventos:
                h = (e.get('hora') or "--:--")[:5]
                a = e.get('altura') or "--"
                t = (e.get('tipo') or "").lower()
                
                info = f"{h} ({a}m)"
                if 'pleamar' in t:
                    pleas.append(info)
                elif 'bajamar' in t:
                    bajas.append(info)
            
            return {
                "p1": pleas[0] if len(pleas) > 0 else "--:--",
                "p2": pleas[1] if len(pleas) > 1 else "--:--",
                "b1": bajas[0] if len(bajas) > 0 else "--:--",
                "b2": bajas[1] if len(bajas) > 1 else "--:--",
                "puerto": "Bermeo (ID:72)",
                "origen": "📡 IHM API Zuzena"
            }
        else:
            return {"error": f"Zerbitzariaren erantzun okerra: {res.status_code}"}
            
    except Exception as e:
        return {"error": "Ezin izan da zerbitzariarekin konektatu."}

# --- INTERFAZ NAGUSIA ---
st.sidebar.title("⚓ UR Abentura")
centro = st.sidebar.radio("Zentroa aukeratu:", list(BASES.keys()))
info = BASES[centro]

st.title(f"📍 {centro}")

if info['tipo'] == "mar":
    st.subheader(f"🌊 Mareak / Mareas ({datetime.date.today().strftime('%d/%m/%Y')})")
    
    with st.spinner("Bermeoko datuak kargatzen..."):
        m = consultar_api_marea(info['id_ihm'], datetime.date.today())
        
        if m and "error" not in m:
            st.caption(f"Iturria: {m['origen']} | Portua: {m['puerto']}")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"⬆️ **Gora / Pleamar**\n\n1: {m['p1']}\n\n2: {m['p2']}")
            with col2:
                st.warning(f"⬇️ **Behera / Bajamar**\n\n1: {m['b1']}\n\n2: {m['b2']}")
        else:
            st.error(f"⚠️ Errorea: {m.get('error', 'Konexio ezezaguna')}")
            st.info("💡 Aholkua: Webgune militarrak askotan blokeatzen dituzte Streamlit-en konexioak. Erabili CSV-a APIak huts egiten badu.")

    # BILATZAILEA
    st.divider()
    st.subheader("🔍 Marea Bilatzailea (Bermeo)")
    fecha_bus = st.date_input("Data:", datetime.date.today())
    if st.button("Bilatu"):
        res = consultar_api_marea(info['id_ihm'], fecha_bus)
        if res and "error" not in res:
            st.success(f"Datuak: {fecha_bus}")
            st.write(f"**Gora:** {res['p1']} | {res['p2']}  \n**Behera:** {res['b1']} | {res['b2']}")
        else:
            st.error("Errorea datu hauek bilatzean.")
else:
    st.info("Mendexa: Mendi parkea. Ez dago marearik.")

st.divider()
st.caption("UR line © 2026 - Bermeoko Erreferentzia Sistema")
