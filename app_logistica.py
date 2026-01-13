import streamlit as st
import pandas as pd
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Logística Ourense Pro", layout="wide")

st.title("🚛 Calculadora Logística Interactiva")
st.markdown("Carga tus clientes desde Excel o busca direcciones en tiempo real.")

# --- 0. INICIALIZAR MEMORIA (SESSION STATE) ---
if 'target_coords' not in st.session_state:
    st.session_state['target_coords'] = None
if 'target_name' not in st.session_state:
    st.session_state['target_name'] = ""
if 'km_result' not in st.session_state:
    st.session_state['km_result'] = 0
if 'zona_info' not in st.session_state:
    st.session_state['zona_info'] = None

# --- 1. CARGA DE DATOS ---
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
        # Datos por defecto (CORREGIDO: 14 elementos en cada lista)
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

# --- 2. INTERFAZ PRINCIPAL ---
col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.subheader("📍 Calcular Ruta")
    entrada = st.text_input("Escribe CP, Pueblo o Cliente:", placeholder="Ej: 32500 o 36004")
    btn_calc = st.button("Buscar y Calcular", type="primary")

    # --- LÓGICA DE CÁLCULO ---
    if btn_calc and entrada:
        with st.spinner("Localizando..."):
            # 1. Inicializamos variables
            target_coords = None
            target_name = ""
            
            # 2. Buscar en base de datos interna/Excel
            if df_datos is not None:
                busqueda = df_datos[
                    (df_datos['CP'].astype(str) == entrada) | 
                    (df_datos['City'].str.contains(entrada, case=False, na=False))
                ]
                if not busqueda.empty:
                    target_coords = (busqueda.iloc[0]['Lat'], busqueda.iloc[0]['Lon'])
                    target_name = f"{busqueda.iloc[0]['City']} (Cliente Registrado)"
            
            # 3. Búsqueda Online Inteligente
            if not target_coords:
                geolocator = Nominatim(user_agent="app_logistica_final_v2")
                try:
                    busqueda_gps = ""
                    if entrada.isdigit() and len(entrada) == 5:
                        busqueda_gps = f"{entrada}, España"
                    else:
                        busqueda_gps = f"{entrada}, Ourense, España"

                    loc = geolocator.geocode(busqueda_gps, timeout=10)
                    
                    if not loc and not entrada.isdigit():
                         loc = geolocator.geocode(f"{entrada}, España", timeout=10)

                    if loc:
                        target_coords = (loc.latitude, loc.longitude)
                        target_name = loc.address.split(",")[0]
                    else:
                        st.warning(f"⚠️ No se encontró la dirección: {entrada}")

                except Exception as e:
                    st.error(f"⚠️ Error técnico: {e}")

            # 4. Guardar resultados en Memoria
            if target_coords:
                st.session_state['target_coords'] = target_coords
                st.session_state['target_name'] = target_name
                
                km = round(geodesic(origen_ourense, target_coords).km, 2)
                st.session_state['km_result'] = km
                
                if km <= 20:
                    st.session_state['zona_info'] = ("ZONA 1 (0-20km)", "#FFF176")
                elif km <= 50:
                    st.session_state['zona_info'] = ("ZONA 2 (20-50km)", "#FF8A80")
                elif km <= 100:
                    st.session_state['zona_info'] = ("ZONA 3 (50-100km)", "#81D4FA")
                else:
                    st.session_state['zona_info'] = ("ZONA 4 (>100km)", "#A5D6A7")
            else:
                st.session_state['target_coords'] = None

    # MOSTRAR RESULTADOS
    if st.session_state['target_coords']:
        zona, color = st.session_state['zona_info']
        km = st.session_state['km_result']
        name = st.session_state['target_name']
        
        st.markdown(f"""
        <div style='background-color:{color}; padding:15px; border-radius:10px; border:1px solid #ccc; color:black; margin-top:20px;'>
            <h3 style='margin:0'>{zona}</h3>
            <p style='font-size:18px; margin:5px 0'>Distancia: <strong>{km} km</strong></p>
            <p style='font-size:14px; margin:0'>Destino: {name}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🗑️ Limpiar búsqueda"):
            st.session_state['target_coords'] = None
            st.rerun()

with col_der:
    st.subheader("🗺️ Mapa Interactivo")
    
    m = folium.Map(location=origen_ourense, zoom_start=9)

    # Zonas
    folium.Circle(origen_ourense, radius=20000, color="gold", fill=True, fill_opacity=0.1).add_to(m)
    folium.Circle(origen_ourense, radius=50000, color="red", fill=False, weight=2).add_to(m)
    folium.Circle(origen_ourense, radius=100000, color="blue", fill=False, weight=2, linestyle='--').add_to(m)

    # Clientes
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

    # Resultado búsqueda
    if st.session_state['target_coords']:
        target = st.session_state['target_coords']
        folium.Marker(
            target,
            popup="DESTINO",
            icon=folium.Icon(color="green", icon="flag")
        ).add_to(m)
        folium.PolyLine([origen_ourense, target], color="black", weight=3).add_to(m)

    st_folium(m, width="100%", height=600)
