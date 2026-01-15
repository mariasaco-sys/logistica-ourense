import streamlit as st
import pandas as pd
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import requests # Necesario para preguntar al servidor de mapas
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Logística Ourense Pro", layout="wide")

st.title("🚛 Calculadora Logística (Rutas Reales)")
st.markdown("Calcula distancia real por carretera, transporte y costes.")

# --- 0. INICIALIZAR MEMORIA ---
if 'target_coords' not in st.session_state: st.session_state['target_coords'] = None
if 'target_name' not in st.session_state: st.session_state['target_name'] = ""
if 'km_result' not in st.session_state: st.session_state['km_result'] = 0
if 'tipo_calculo' not in st.session_state: st.session_state['tipo_calculo'] = "" # Para saber si es lineal o real
if 'zona_info' not in st.session_state: st.session_state['zona_info'] = None
if 'logistica_transporte' not in st.session_state: st.session_state['logistica_transporte'] = ""
if 'logistica_frecuencia' not in st.session_state: st.session_state['logistica_frecuencia'] = ""
if 'logistica_acarreo' not in st.session_state: st.session_state['logistica_acarreo'] = ""

# --- 1. FUNCIÓN GPS CARRETERA (NUEVO) ---
def obtener_distancia_carretera(origen, destino):
    """
    Conecta con OSRM para obtener distancia real por carretera.
    origen y destino deben ser tuplas (lat, lon).
    """
    # OSRM quiere las coordenadas al revés: (longitud, latitud)
    url = f"http://router.project-osrm.org/route/v1/driving/{origen[1]},{origen[0]};{destino[1]},{destino[0]}?overview=false"
    
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            datos = r.json()
            # La distancia viene en metros
            distancia_metros = datos['routes'][0]['distance']
            return round(distancia_metros / 1000, 2), "🚗 Por Carretera"
    except:
        pass # Si falla el servidor, pasamos al plan B
    
    # Plan B: Si el servidor falla, usamos línea recta y avisamos
    dist_lineal = round(geodesic(origen, destino).km, 2)
    return dist_lineal, "✈️ Línea Recta (Servidor ocupado)"

# --- 2. REGLAS LOGÍSTICAS ---
def calcular_reglas_logistica(cp_detectado):
    cp = str(cp_detectado).strip()
    if not cp or not cp[0].isdigit(): return "❓ Consultar", "Depende destino", "❓"

    # REGLAS (Editables)
    if cp.startswith("32"): return "🚛 FLOTA PROPIA", "⚡ Diaria (L-V)", "❌ No"
    elif cp.startswith("36"): return "🚚 AGENCIA RÍAS BAIXAS", "📅 L-X-V", "⚠️ Sí (Zona Acarreo)"
    elif cp.startswith("15") or cp.startswith("27"): return "🚚 AGENCIA NORTE", "📅 M-J", "❌ No"
    else: return "✈️ RED NACIONAL", "⏱️ 48/72h", "⚠️ Sí"

# --- 3. CARGA DATOS ---
st.sidebar.header("📂 Gestión de Datos")
uploaded_file = st.sidebar.file_uploader("Sube Excel Clientes", type=["xlsx"])
@st.cache_data
def obtener_datos(archivo):
    if archivo:
        try: return pd.read_excel(archivo)
        except: return None
    return pd.DataFrame({
            'City': ['Ourense', 'Barbadás', 'San Cibrao', 'Pereiro', 'O Carballiño', 'Ribadavia', 'Vigo'],
            'CP': ['32001', '32890', '32901', '32710', '32500', '32400', '36201'],
            'Lat': [42.3358, 42.3022, 42.2965, 42.3467, 42.4300, 42.2878, 42.2406],
            'Lon': [-7.8639, -7.8967, -7.8676, -7.8000, -8.0772, -8.1430, -8.7207]
    })
df_datos = obtener_datos(uploaded_file)
origen_ourense = (42.3358, -7.8639)

# --- 4. BÚSQUEDA GPS ---
def buscar_con_reintentos(query_dict_or_str, intentos=2):
    geolocator = Nominatim(user_agent="app_logistica_v9_road")
    for i in range(intentos):
        try:
            if i > 0: time.sleep(1)
            if isinstance(query_dict_or_str, dict):
                return geolocator.geocode(query_dict_or_str, timeout=10, addressdetails=True)
            else:
                return geolocator.geocode(query_dict_or_str, timeout=10, addressdetails=True)
        except: continue
    return None

# --- INTERFAZ ---
col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.subheader("📍 Datos del Envío")
    entrada = st.text_input("Destino (CP, Pueblo...):", placeholder="Ej: 36004")
    btn_calc = st.button("🔍 Calcular Ruta Real", type="primary")

    if btn_calc and entrada:
        with st.spinner("Calculando ruta por carretera..."):
            target_coords, target_name, cp_final = None, "", ""
            
            # 1. Buscar Coordenadas
            if df_datos is not None:
                mask = (df_datos['CP'].astype(str) == entrada) | (df_datos['City'].str.contains(entrada, case=False, na=False))
                busqueda = df_datos[mask]
                if not busqueda.empty:
                    target_coords = (busqueda.iloc[0]['Lat'], busqueda.iloc[0]['Lon'])
                    target_name = f"{busqueda.iloc[0]['City']} (Cliente)"
                    cp_final = str(busqueda.iloc[0]['CP'])
            
            if not target_coords:
                loc = None
                if entrada.isdigit() and len(entrada) == 5:
                    loc = buscar_con_reintentos({"postalcode": entrada, "country": "Spain"})
                    cp_final = entrada
                else:
                    loc = buscar_con_reintentos(f"{entrada}, España")
                    if not loc: loc = buscar_con_reintentos(f"{entrada}, Ourense, España")
                    if loc and 'address' in loc.raw and 'postcode' in loc.raw['address']:
                        cp_final = loc.raw['address']['postcode']
                
                if loc:
                    target_coords = (loc.latitude, loc.longitude)
                    target_name = loc.address.split(",")[0]

            # 2. Calcular Todo (AHORA CON CARRETERA)
            if target_coords:
                # --- AQUÍ ESTÁ EL CAMBIO CLAVE ---
                km, tipo_calc = obtener_distancia_carretera(origen_ourense, target_coords)
                # ---------------------------------
                
                # Zonas
                if km <= 20: zona_res = ("ZONA 1 (0-20km)", "#FFF9C4")
                elif km <= 50: zona_res = ("ZONA 2 (20-50km)", "#FFCCBC")
                elif km <= 100: zona_res = ("ZONA 3 (50-100km)", "#B3E5FC")
                else: zona_res = ("ZONA 4 (>100km)", "#C8E6C9")
                
                # Logística
                t, f, a = calcular_reglas_logistica(cp_final)

                st.session_state.update({
                    'target_coords': target_coords, 'target_name': target_name,
                    'km_result': km, 'tipo_calculo': tipo_calc, 'zona_info': zona_res,
                    'logistica_transporte': t, 'logistica_frecuencia': f, 'logistica_acarreo': a
                })
            else:
                st.warning("⚠️ Destino no encontrado")

    # RESULTADOS
    if st.session_state['target_coords']:
        zona_txt, bg_color = st.session_state['zona_info']
        st.markdown(f"""
        <div style='background-color: {bg_color}; padding: 15px; border-radius: 10px; border: 1px solid #ccc; color: black;'>
            <h3 style='margin-top:0;'>{st.session_state['target_name']}</h3>
            <table style='width:100%'>
                <tr><td>🛣️ <strong>Distancia:</strong></td><td>{st.session_state['km_result']} km <small>({st.session_state['tipo_calculo']})</small></td></tr>
                <tr><td>📍 <strong>Zona:</strong></td><td>{zona_txt}</td></tr>
                <tr><td>🚛 <strong>Transporte:</strong></td><td>{st.session_state['logistica_transporte']}</td></tr>
                <tr><td>📅 <strong>Frecuencia:</strong></td><td>{st.session_state['logistica_frecuencia']}</td></tr>
                <tr><td>📦 <strong>Acarreo:</strong></td><td>{st.session_state['logistica_acarreo']}</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

with col_der:
    st.subheader("🗺️ Mapa de Ruta")
    m = folium.Map(location=origen_ourense, zoom_start=9)
    
    # Círculos Zonas
    folium.Circle(origen_ourense, radius=20000, color="gold", fill=True, fill_opacity=0.1).add_to(m)
    folium.Circle(origen_ourense, radius=50000, color="red", fill=False, weight=2).add_to(m)
    
    # Marcadores
    if df_datos is not None:
        for idx, row in df_datos.iterrows():
            folium.Marker([row['Lat'], row['Lon']], popup=row['City'], icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)
    
    if st.session_state['target_coords']:
        target = st.session_state['target_coords']
        folium.Marker(target, popup="DESTINO", icon=folium.Icon(color="green", icon="flag")).add_to(m)
        # Línea recta visual (dibujar la carretera real en el mapa es más complejo, mantenemos la línea visual)
        folium.PolyLine([origen_ourense, target], color="black", weight=3, opacity=0.7, dash_array='5, 10').add_to(m)

    st_folium(m, width="100%", height=600)
