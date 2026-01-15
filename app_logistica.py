import streamlit as st
import pandas as pd
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Logística Ourense Pro", layout="wide")

st.title("🚛 Calculadora Logística Interactiva")
st.markdown("Calcula rutas, asigna transportistas y frecuencias automáticamente según el CP.")

# --- 0. INICIALIZAR MEMORIA ---
if 'target_coords' not in st.session_state:
    st.session_state['target_coords'] = None
if 'target_name' not in st.session_state:
    st.session_state['target_name'] = ""
if 'km_result' not in st.session_state:
    st.session_state['km_result'] = 0
if 'zona_info' not in st.session_state:
    st.session_state['zona_info'] = None
# Nuevas variables para guardar la info logística
if 'transporte_info' not in st.session_state:
    st.session_state['transporte_info'] = None
if 'frecuencia_info' not in st.session_state:
    st.session_state['frecuencia_info'] = None

# --- 1. LÓGICA LOGÍSTICA (NUEVO) ---
def obtener_info_logistica(cp_str):
    """
    Define el transporte y frecuencia según el prefijo del Código Postal.
    Puedes editar estas reglas según tus necesidades reales.
    """
    # Nos aseguramos de tener un string limpio
    cp = str(cp_str).strip()
    
    # REGLA 1: Ourense (32xxx)
    if cp.startswith("32"):
        return "🚛 FLOTA PROPIA", "📅 Diaria (Lunes a Viernes)"
    
    # REGLA 2: Pontevedra (36xxx)
    elif cp.startswith("36"):
        return "🚚 AGENCIA GALICIA SUR", "📅 Lunes, Miércoles, Viernes"
        
    # REGLA 3: A Coruña (15xxx) y Lugo (27xxx)
    elif cp.startswith("15") or cp.startswith("27"):
        return "🚚 AGENCIA GALICIA NORTE", "📅 Martes y Jueves"
    
    # REGLA 4: Resto de España
    else:
        return "✈️ RED NACIONAL", "⏱️ 48/72 Horas"

# --- 2. CARGA DE DATOS ---
st.sidebar.header("📂 Gestión de Datos")
uploaded_file = st.sidebar.file_uploader("Sube tu Excel de clientes (Opcional)", type=["xlsx"])

@st.cache_data
def obtener_datos(archivo):
    if archivo is not None:
        try:
            df = pd.read_excel(archivo)
            required_cols = ['City', 'CP', 'Lat', 'Lon']
            if not all(col in df.columns for col in required_cols):
                st.error(f"El Excel debe tener las columnas: {required_cols}")
                return None
            return df
        except Exception as e:
            st.error(f"Error al leer el archivo: {e}")
            return None
    else:
        # Datos por defecto
        data = {
            'City': ['Ourense', 'Barbadás', 'San Cibrao', 'Pereiro', 'O Carballiño', 'Ribadavia',
                     'Allariz', 'Maceda', 'Celanova', 'Xinzo', 'Monforte', 'Lalín', 'Santiago', 'Vigo'],
            'CP': ['32001', '32890', '32901', '32710', '32500', '32400',
                   '32660', '32700', '32800', '32630', '27400', '36500', '15701', '36201'],
            'Lat': [42.3358, 42.3022, 42.2965, 42.3467, 42.4300, 42.2878,
                    42.1911, 42.2706, 42.1517, 42.0634, 42.5218, 42.6617, 42.8782, 42.2406],
            'Lon': [-7.8639, -7.8967, -7.8676, -7.8000, -8.0772, -8.1430,
                    -7.8016, -7.6517, -7.9575, -7.7257, -7.5144, -8.1132, -8.5448, -8.7207]
        }
        return pd.DataFrame(data)

df_datos = obtener_datos(uploaded_file)
origen_ourense = (42.3358, -7.8639)

# --- FUNCIÓN DE BÚSQUEDA ---
def buscar_con_reintentos(query_dict_or_str, intentos=3):
    geolocator = Nominatim(user_agent="app_logistica_v7_transport")
    for i in range(intentos):
        try:
            if i > 0: time.sleep(1.5) 
            if isinstance(query_dict_or_str, dict):
                return geolocator.geocode(query_dict_or_str, timeout=10)
            else:
                return geolocator.geocode(query_dict_or_str, timeout=10)
        except Exception:
            continue
    return None

# --- 3. INTERFAZ PRINCIPAL ---
col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.subheader("📍 Calcular Ruta")
    entrada = st.text_input("Escribe CP o Ciudad:", placeholder="Ej: 36004")
    btn_calc = st.button("Buscar y Calcular", type="primary")

    if btn_calc and entrada:
        with st.spinner("Calculando ruta y logística..."):
            target_coords = None
            target_name = ""
            cp_detectado = "" # Variable para guardar el CP encontrado
            
            # A) Buscar en Base de Datos (Excel/Interna)
            if df_datos is not None:
                busqueda = df_datos[
                    (df_datos['CP'].astype(str) == entrada) | 
                    (df_datos['City'].str.contains(entrada, case=False, na=False))
                ]
                if not busqueda.empty:
                    target_coords = (busqueda.iloc[0]['Lat'], busqueda.iloc[0]['Lon'])
                    target_name = f"{busqueda.iloc[0]['City']} (Cliente Registrado)"
                    cp_detectado = str(busqueda.iloc[0]['CP'])
            
            # B) Buscar Online
            if not target_coords:
                try:
                    loc = None
                    # Caso CP
                    if entrada.isdigit() and len(entrada) == 5:
                        loc = buscar_con_reintentos({"postalcode": entrada, "country": "Spain"})
                        if loc: cp_detectado = entrada # Si buscamos por CP, ese es el CP
                    
                    # Caso Texto
                    else:
                        loc = buscar_con_reintentos(f"{entrada}, España")
                        if not loc: loc = buscar_con_reintentos(f"{entrada}, Ourense, España")
                        # Si buscamos por nombre, no tenemos el CP exacto fácilmente, 
                        # así que usaremos una lógica genérica o intentaremos extraerlo si fuera posible.
                        # Para simplificar, si no hay CP numérico, asignaremos "Red Nacional" por defecto.

                    if loc:
                        target_coords = (loc.latitude, loc.longitude)
                        target_name = loc.address.split(",")[0]
                    else:
                        st.warning(f"⚠️ No se encontró: '{entrada}'.")

                except Exception as e:
                    st.error(f"⚠️ Error: {e}")

            # C) Procesar Resultados
            if target_coords:
                # 1. Guardar datos básicos
                st.session_state['target_coords'] = target_coords
                st.session_state['target_name'] = target_name
                
                # 2. Calcular Distancia y Zona
                km = round(geodesic(origen_ourense, target_coords).km, 2)
                st.session_state['km_result'] = km
                
                if km <= 20: st.session_state['zona_info'] = ("ZONA 1 (0-20km)", "#FFF176")
                elif km <= 50: st.session_state['zona_info'] = ("ZONA 2 (20-50km)", "#FF8A80")
                elif km <= 100: st.session_state['zona_info'] = ("ZONA 3 (50-100km)", "#81D4FA")
                else: st.session_state['zona_info'] = ("ZONA 4 (>100km)", "#A5D6A7")
                
                # 3. CALCULAR LOGÍSTICA (NUEVO)
                # Si tenemos un CP detectado, usamos la función. Si no, valor por defecto.
                if cp_detectado:
                    transporte, frecuencia = obtener_info_logistica(cp_detectado)
                else:
                    # Si buscó por nombre de pueblo y no sabemos el CP exacto
                    transporte, frecuencia = "Consultar Agencia", "Depende del destino"
                
                st.session_state['transporte_info'] = transporte
                st.session_state['frecuencia_info'] = frecuencia

            else:
                st.session_state['target_coords'] = None

    # MOSTRAR RESULTADOS
    if st.session_state['target_coords']:
        zona, color = st.session_state['zona_info']
        km = st.session_state['km_result']
        name = st.session_state['target_name']
        transp = st.session_state['transporte_info']
        freq = st.session_state['frecuencia_info']
        
        st.markdown(f"""
        <div style='background-color:{color}; padding:20px; border-radius:15px; border:2px solid #ddd; color:black; margin-top:20px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);'>
            <h2 style='margin:0; color:#333;'>{zona}</h2>
            <hr style='border:1px solid #999; margin:10px 0;'>
            <p style='font-size:18px; margin:5px 0'>📍 Destino: <strong>{name}</strong></p>
            <p style='font-size:18px; margin:5px 0'>📏 Distancia: <strong>{km} km</strong></p>
            <div style='background-color:rgba(255,255,255,0.5); padding:10px; border-radius:10px; margin-top:10px;'>
                <p style='font-size:16px; margin:5px 0; color:#005580;'>{transp}</p>
                <p style='font-size:16px; margin:5px 0; color:#005580;'>{freq}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🗑️ Nueva búsqueda"):
            st.session_state['target_coords'] = None
            st.rerun()

with col_der:
    st.subheader("🗺️ Mapa Interactivo")
    
    m = folium.Map(location=origen_ourense, zoom_start=9)

    # Zonas
    folium.Circle(origen_ourense, radius=20000, color="gold", fill=True, fill_opacity=0.1).add_to(m)
    folium.Circle(origen_ourense, radius=50000, color="red", fill=False, weight=2).add_to(m)
    folium.Circle(origen_ourense, radius=100000, color="blue", fill=False, weight=2, linestyle='--').add_to(m)

    # Clientes Excel
    if df_datos is not None:
        for idx, row in df_datos.iterrows():
            folium.Marker(
                [row['Lat'], row['Lon']],
                popup=f"{row['City']} ({row['CP']})",
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)
            
            folium.map.Marker(
                [row['Lat'], row['Lon']],
                icon=DivIcon(
                    icon_size=(150,36),
                    icon_anchor=(-10,0),
                    html=f'<div style="font-size: 8pt; font-weight: bold; color: black; background-color: rgba(255,255,255,0.6); padding: 1px; border-radius: 3px; display: inline-block;">{row["City"]}</div>',
                )
            ).add_to(m)

    # Resultado
    if st.session_state['target_coords']:
        target = st.session_state['target_coords']
        folium.Marker(
            target,
            popup="DESTINO",
            icon=folium.Icon(color="green", icon="flag")
        ).add_to(m)
        folium.PolyLine([origen_ourense, target], color="black", weight=3).add_to(m)

    st_folium(m, width="100%", height=600)

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
