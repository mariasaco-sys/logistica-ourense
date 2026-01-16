import streamlit as st
import pandas as pd
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import requests
import time
import io
import random

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Logística Ourense Pro", layout="wide")

st.title("🚛 Calculadora Logística Ourense")
st.markdown("Sistema de gestión de rutas con cálculo de distancia garantizado.")

# --- 1. BASE DE DATOS DE COORDENADAS (RESPALDO DE SEGURIDAD) ---
COORDENADAS_FIJAS = {
    "32001": (42.3358, -7.8639), "32002": (42.3358, -7.8639), "32003": (42.3358, -7.8639),
    "32004": (42.3358, -7.8639), "32005": (42.3358, -7.8639), # Ourense Centro
    "32900": (42.2965, -7.8676), "32901": (42.2965, -7.8676), # Polígono San Cibrao
    "32911": (42.2965, -7.8676), "32910": (42.2965, -7.8676),
    "27400": (42.5218, -7.5144), # Monforte
    "27500": (42.6075, -7.7121), # Chantada
    "32500": (42.4300, -8.0772), # Carballiño
    "32400": (42.2878, -8.1430), # Ribadavia
    "32630": (42.0634, -7.7257), # Xinzo
    "32600": (41.9366, -7.4393), # Verín
    "32300": (42.4168, -6.9839), "32315": (42.4168, -6.9839), # O Barco
    "36500": (42.6617, -8.1132), # Lalín
    "32660": (42.1911, -7.8016), # Allariz
    "32700": (42.2706, -7.6517), # Maceda
    "32800": (42.1517, -7.9575), # Celanova
    "32130": (42.4736, -7.9825), # Cea
    "32720": (42.3255, -7.6997), # Esgos
    "32760": (42.3736, -7.4158), # Castro Caldelas
    "32780": (42.3411, -7.2839), # Trives
    "32570": (42.4627, -8.0261)  # Maside
}

# --- 2. DATOS HISTÓRICOS ---
CSV_DATA = """Ruta_Asignada,Código postal envío,Ciudad_Clean,Num_Pedidos_Historico,Dia_Asignado
EJE ESTE (N-120),27400,MONFORTE DE LEMOS,29,Jueves
EJE ESTE (N-120),27500,CHANTADA,15,Jueves
EJE ESTE (N-120),32720,ESGOS,10,Jueves
EJE ESTE (N-120),32700,MACEDA,9,Jueves
EJE ESTE (N-120),27513,CHANTADA,7,Jueves
EJE ESTE (N-120),32706,MACEDA,6,Jueves
EJE ESTE (N-120),32760,CASTRO CALDELAS,5,Jueves
EJE ESTE (N-120),27400,MONFORTE,4,Jueves
EJE ESTE (N-120),32780,PUEBLA DE TRIVES,4,Jueves
EJE ESTE (N-120),27514,CHANTADA,3,Jueves
EJE ESTE (N-120),27320,"QUIROGA , MONFORTE",2,Jueves
EJE ESTE (N-120),27400,MONFORTE DE LEMOS CASCO URBANO,2,Jueves
EJE ESTE (N-120),27500,CHANTADA LUGO,2,Jueves
EJE ESTE (N-120),27517,CHANTADA,2,Jueves
EJE ESTE (N-120),27590,MONFORTE DE LEMOS,2,Jueves
EJE ESTE (N-120),32315,O BARCO DE VALDEORRAS,2,Jueves
EJE ESTE (N-120),32350,A RUA,2,Jueves
EJE ESTE (N-120),32766,CASTRO CALDELAS,2,Jueves
EJE ESTE (N-120),32769,CASTRO CALDELAS,2,Jueves
EJE ESTE (N-120),27400,MONFORTE DE LEMOS (GULLADE ),1,Jueves
EJE ESTE (N-120),27410,MONFORTE DE LEMOS,1,Jueves
EJE ESTE (N-120),27417,MONFORTE DE LEMOS,1,Jueves
EJE ESTE (N-120),27420,MONFORTE DE LEMOS,1,Jueves
EJE ESTE (N-120),27420,PIÑEIRA SAN MARTIÑO MONFORTE,1,Jueves
EJE ESTE (N-120),27512,LAXE XOANIN - CHANTADA,1,Jueves
EJE ESTE (N-120),27513,REQUEIXO CHANTADA,1,Jueves
EJE ESTE (N-120),27519,CHANTADA,1,Jueves
EJE ESTE (N-120),27595,CHANTADA,1,Jueves
EJE ESTE (N-120),32002,CHANTADA,1,Jueves
EJE ESTE (N-120),32300,"BARCO, O",1,Jueves
EJE ESTE (N-120),32300,O BARCO,1,Jueves
EJE ESTE (N-120),32300,O BARCO DE VALDEORRAS,1,Jueves
EJE ESTE (N-120),32350,A RUA DE VALDEORRAS,1,Jueves
EJE ESTE (N-120),32357,ROBLIDO A RUA,1,Jueves
EJE ESTE (N-120),32700,CASTRO CALDELAS,1,Jueves
EJE ESTE (N-120),32700,ORENSE MACEDA,1,Jueves
EJE ESTE (N-120),32708,MACEDA,1,Jueves
EJE ESTE (N-120),32720,GOMARIZ ESGOS,1,Jueves
EJE ESTE (N-120),32740,MACEDA,1,Jueves
EJE ESTE (N-120),32794,CASTRO CALDELAS,1,Jueves
EJE NORTE (AG-53/A-52),32500,O CARBALLIÑO,36,Martes
EJE NORTE (AG-53/A-52),32400,RIBADAVIA,15,Martes
EJE NORTE (AG-53/A-52),32520,AVION,10,Martes
EJE NORTE (AG-53/A-52),36500,LALIN,10,Martes
EJE NORTE (AG-53/A-52),32500,"CARBALLIÑO, O",7,Martes
EJE NORTE (AG-53/A-52),32130,SAN CRISTOVO DE CEA,6,Martes
EJE NORTE (AG-53/A-52),32420,LEIRO,6,Martes
EJE NORTE (AG-53/A-52),32426,LEIRO,3,Martes
EJE NORTE (AG-53/A-52),32570,MASIDE,3,Martes
EJE NORTE (AG-53/A-52),32418,RIBADAVIA,2,Martes
EJE NORTE (AG-53/A-52),32419,"VIEITE, LEIRO",2,Martes
EJE NORTE (AG-53/A-52),32420,LEBOSENDE- LEIRO,2,Martes
EJE NORTE (AG-53/A-52),32428,LEIRO,2,Martes
EJE NORTE (AG-53/A-52),32573,MASIDE,2,Martes
EJE NORTE (AG-53/A-52),36512,LALIN,2,Martes
EJE NORTE (AG-53/A-52),15172,OLEIROS,1,Martes
EJE NORTE (AG-53/A-52),15176,OLEIROS,1,Martes
EJE NORTE (AG-53/A-52),32139,BOBORAS,1,Martes
EJE NORTE (AG-53/A-52),32141,CEA,1,Martes
EJE NORTE (AG-53/A-52),32141,SAN CRISTOBAL DE CEA,1,Martes
EJE NORTE (AG-53/A-52),32141,SAN CRISTOBO DE CEA,1,Martes
EJE NORTE (AG-53/A-52),32141,SAN CRISTOVO DE CEA,1,Martes
EJE NORTE (AG-53/A-52),32410,MELON,1,Martes
EJE NORTE (AG-53/A-52),32411,MELON,1,Martes
EJE NORTE (AG-53/A-52),32415,RIBADAVIA,1,Martes
EJE NORTE (AG-53/A-52),32415,VENTOSELA (RIBADAVIA ),1,Martes
EJE NORTE (AG-53/A-52),32416,RIBADAVIA,1,Martes
EJE NORTE (AG-53/A-52),32416,"SAN CRISTOBAL, RIBADAVIA",1,Martes
EJE NORTE (AG-53/A-52),32418,FRANCELOS - RIBADAVIA,1,Martes
EJE NORTE (AG-53/A-52),32418,SAMPAIO RIBADAVIA,1,Martes
EJE NORTE (AG-53/A-52),32418,"SANPAIO, RIBADAVIA",1,Martes
EJE NORTE (AG-53/A-52),32420,O CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32425,LEIRO,1,Martes
EJE NORTE (AG-53/A-52),32429,LEIRO,1,Martes
EJE NORTE (AG-53/A-52),32500,CARBALLIÑO - ARCOS,1,Martes
EJE NORTE (AG-53/A-52),32500,CONCELLO DE CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32500,MAGARIÑOS-O CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32510,O CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32514,"ALBARELLOS,BOBORAS",1,Martes
EJE NORTE (AG-53/A-52),32514,BOBORAS,1,Martes
EJE NORTE (AG-53/A-52),32514,BOBORAS VILACHA CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32515,O CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32515,PARTOVIA - O CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32520,"BARROSO, DE AVION",1,Martes
EJE NORTE (AG-53/A-52),32534,O CARBALLIÑO,1,Martes
EJE NORTE (AG-53/A-52),32570,O LAGO MASIDE,1,Martes
EJE NORTE (AG-53/A-52),32573,CONCELLO DE MASIDE,1,Martes
EJE NORTE (AG-53/A-52),32574,MASIDE,1,Martes
EJE NORTE (AG-53/A-52),32577,"LOUREDO, MASIDE",1,Martes
EJE NORTE (AG-53/A-52),36510,LALIN,1,Martes
EJE NORTE (AG-53/A-52),36540,SILLEDA,1,Martes
EJE SUR (A-52),32630,XINZO DE LIMIA,28,Miércoles
EJE SUR (A-52),32600,VERIN,26,Miércoles
EJE SUR (A-52),32660,ALLARIZ,25,Miércoles
EJE SUR (A-52),32112,PADERNE DE ALLARIZ,12,Miércoles
EJE SUR (A-52),32670,XUNQUEIRA DE AMBIA,8,Miércoles
EJE SUR (A-52),32664,ALLARIZ,6,Miércoles
EJE SUR (A-52),32667,ALLARIZ,6,Miércoles
EJE SUR (A-52),32692,SANDIAS,6,Miércoles
EJE SUR (A-52),32668,ALLARIZ,5,Miércoles
EJE SUR (A-52),32870,LOBIOS,5,Miércoles
EJE SUR (A-52),32610,RIOS,4,Miércoles
EJE SUR (A-52),32892,LOBIOS,4,Miércoles
EJE SUR (A-52),32637,XINZO DE LIMIA,3,Miércoles
EJE SUR (A-52),32665,ALLARIZ,3,Miércoles
EJE SUR (A-52),32678,XUNQUEIRA DE AMBIA,3,Miércoles
EJE SUR (A-52),32689,CUALEDRO,3,Miércoles
EJE SUR (A-52),32695,TRASMIRAS,3,Miércoles
EJE SUR (A-52),27423,LOBIOS,2,Miércoles
EJE SUR (A-52),32627,TINTORES VERIN,2,Miércoles
EJE SUR (A-52),32632,XINZO DE LIMIA,2,Miércoles
EJE SUR (A-52),32636,XINZO DE LIMIA MORGADE,2,Miércoles
EJE SUR (A-52),32650,XINZO VILAR DE SANTOS,2,Miércoles
EJE SUR (A-52),32678,CONCELLO DE XUNQUEIRA DE AMBIA,2,Miércoles
EJE SUR (A-52),32680,CUALEDRO,2,Miércoles
EJE SUR (A-52),32688,CUALEDRO,2,Miércoles
EJE SUR (A-52),32895,LOBIOS,2,Miércoles
EJE SUR (A-52),32111,PADERNE ALLARIZ,1,Miércoles
EJE SUR (A-52),32111,PADERNE DE ALLARIZ,1,Miércoles
EJE SUR (A-52),32111,SANCRISTVO PADERNE DE ALLARIZ,1,Miércoles
EJE SUR (A-52),32112,PDERNE DE ALLARIZ,1,Miércoles
EJE SUR (A-52),32525,ALLARIZ DOADE,1,Miércoles
EJE SUR (A-52),32610,COVELAS RIOS,1,Miércoles
EJE SUR (A-52),32611,RIOS,1,Miércoles
EJE SUR (A-52),32611,VERIN,1,Miércoles
EJE SUR (A-52),32614,VERIN,1,Miércoles
EJE SUR (A-52),32618,MEDEIROS MONTERREI,1,Miércoles
EJE SUR (A-52),32618,MONTERREI,1,Miércoles
EJE SUR (A-52),32618,VERIN,1,Miércoles
EJE SUR (A-52),32618,VILLAZA DE MONTERREI,1,Miércoles
EJE SUR (A-52),32619,CONCELLO DE MONTERREI,1,Miércoles
EJE SUR (A-52),32630,XINZO,1,Miércoles
EJE SUR (A-52),32631,XINZO DE LIMIA,1,Miércoles
EJE SUR (A-52),32635,XINZO DE LIMIA,1,Miércoles
EJE SUR (A-52),32636,XINZO DE LIMIA,1,Miércoles
EJE SUR (A-52),32646,"XINZO , BALTAR",1,Miércoles
EJE SUR (A-52),32655,XINZO,1,Miércoles
EJE SUR (A-52),32664,"PENAMA, ALLARIZ",1,Miércoles
EJE SUR (A-52),32667,REQUEIXO DE VALVERDE / ALLARIZ,1,Miércoles
EJE SUR (A-52),32670,XINZO DE LIMIA,1,Miércoles
EJE SUR (A-52),32679,XUNQUEIRA DE AMBIA,1,Miércoles
EJE SUR (A-52),32680,BALDRIZ - CONCELLO DE CUALEDRO .,1,Miércoles
EJE SUR (A-52),32688,PEDROSA CUALEDRO,1,Miércoles
EJE SUR (A-52),32689,CARZOA CUALEDRO,1,Miércoles
EJE SUR (A-52),32696,"LOGOSELO, SARREAUS ,XINZO DE LIMIA",1,Miércoles
EJE SUR (A-52),32696,TRASMIRAS,1,Miércoles
EJE SUR (A-52),32730,XUNQUEIRA DE AMBIA,1,Miércoles
EJE SUR (A-52),32750,XUNQUEIRA DE AMBIA,1,Miércoles
EJE SUR (A-52),32840,LOBIOS,1,Miércoles
EJE SUR (A-52),32869,LOBIOS,1,Miércoles
EJE SUR (A-52),32890,LOBIOS,1,Miércoles
EJE SUR (A-52),32892,XENDIVE (LOBIOS),1,Miércoles
ZONA METRO,32005,OURENSE,162,Lun y Vie
ZONA METRO,32001,OURENSE,135,Lun y Vie
ZONA METRO,32002,OURENSE,105,Lun y Vie
ZONA METRO,32004,OURENSE,89,Lun y Vie
ZONA METRO,32003,OURENSE,44,Lun y Vie
ZONA METRO,32890,BARBADAS,15,Lun y Vie
ZONA METRO,32911,SAN CIBRAO DAS VIÑAS,13,Lun y Vie
ZONA METRO,32710,PEREIRO DE AGUIAR,12,Lun y Vie
ZONA METRO,32170,AMOEIRO,10,Lun y Vie
ZONA METRO,32792,PEREIRO DE AGUIAR,8,Lun y Vie
ZONA METRO,32830,A MERCA,7,Lun y Vie
ZONA METRO,32910,SAN CIBRAO DAS VIÑAS,7,Lun y Vie
ZONA METRO,32172,AMOEIRO,6,Lun y Vie
ZONA METRO,32793,PEREIRO DE AGUIAR,6,Lun y Vie
ZONA METRO,32930,TOEN,6,Lun y Vie
ZONA METRO,32980,AMOEIRO,6,Lun y Vie
ZONA METRO,32002,BARBADAS,5,Lun y Vie
ZONA METRO,32152,COLES,5,Lun y Vie
ZONA METRO,32100,COLES,4,Lun y Vie
ZONA METRO,32710,CORTIÑAS PEREIRO DE AGUIAR,4,Lun y Vie
ZONA METRO,32890,OURENSE,4,Lun y Vie
ZONA METRO,32920,TOEN,4,Lun y Vie
ZONA METRO,32710,O PEREIRO DE AGUIAR,3,Lun y Vie
ZONA METRO,32830,A MANCHICA - A MERCA,3,Lun y Vie
ZONA METRO,32930,BARBADAS,3,Lun y Vie
ZONA METRO,32930,OURENSE,3,Lun y Vie
ZONA METRO,32950,COLES,3,Lun y Vie
ZONA METRO,32950,OURENSE,3,Lun y Vie
ZONA METRO,32981,OURENSE,3,Lun y Vie
ZONA METRO,32001,BARBADAS,2,Lun y Vie
ZONA METRO,32002,A VALENZA,2,Lun y Vie
ZONA METRO,32002,CONCELLO DE OURENSE,2,Lun y Vie
ZONA METRO,32100,OURENSE,2,Lun y Vie
ZONA METRO,32160,NOGUEIRA DE RAMUIN,2,Lun y Vie
ZONA METRO,32160,NOGUEIRA DE RAMUÍN,2,Lun y Vie
ZONA METRO,32161,NOGUEIRA DE RAMUIN,2,Lun y Vie
ZONA METRO,32667,OURENSE,2,Lun y Vie
ZONA METRO,32701,OURENSE,2,Lun y Vie
ZONA METRO,32792,O PEREIRO DE AGUIAR,2,Lun y Vie
ZONA METRO,32792,OURENSE,2,Lun y Vie
ZONA METRO,32811,OURENSE,2,Lun y Vie
ZONA METRO,32890,OURENSE A VALENZA,2,Lun y Vie
ZONA METRO,32901,SAN CIBRAO DAS VINAS,2,Lun y Vie
ZONA METRO,32980,OURENSE,2,Lun y Vie
ZONA METRO,32002,.OURENSE,1,Lun y Vie
ZONA METRO,32002,"A VALENZA, BARBADAS, OURENSE",1,Lun y Vie
ZONA METRO,32002,"A VALENZA,BARBADAS",1,Lun y Vie
ZONA METRO,32005,BARBADAS,1,Lun y Vie
ZONA METRO,32005,SAN CIBRAO DAS VIÑAS,1,Lun y Vie
ZONA METRO,32100,CAMBEO/COLES,1,Lun y Vie
ZONA METRO,32103,OURENSE,1,Lun y Vie
ZONA METRO,32103,OVISO - COLES,1,Lun y Vie
ZONA METRO,32112,OURENSE,1,Lun y Vie
ZONA METRO,32130,OURENSE,1,Lun y Vie
ZONA METRO,32151,OURENSE,1,Lun y Vie
ZONA METRO,32152,MERIZ (COLES),1,Lun y Vie
ZONA METRO,32152,OURENSE,1,Lun y Vie
ZONA METRO,32160,NOGUEIRA DE RAMIUN,1,Lun y Vie
ZONA METRO,32161,NOGUEIRA DE RAMUIN - LUINTRA,1,Lun y Vie
ZONA METRO,32170,AMOEIRO- POVOANZA,1,Lun y Vie
ZONA METRO,32170,OUTEIRO PARADA DE AMOEIRO,1,Lun y Vie
ZONA METRO,32170,PARADA DE AMOEIRO,1,Lun y Vie
ZONA METRO,32172,FIGUEIRAS / AMOEIRO,1,Lun y Vie
ZONA METRO,32212,OURENSE,1,Lun y Vie
ZONA METRO,32213,OURENSE,1,Lun y Vie
ZONA METRO,32229,OURENSE,1,Lun y Vie
ZONA METRO,32235,OURENSE,1,Lun y Vie
ZONA METRO,32235,TRADO PONTE DEVA OURENSE,1,Lun y Vie
ZONA METRO,32236,OURENSE,1,Lun y Vie
ZONA METRO,32400,OURENSE,1,Lun y Vie
ZONA METRO,32413,OURENSE,1,Lun y Vie
ZONA METRO,32418,OURENSE,1,Lun y Vie
ZONA METRO,32430,OURENSE,1,Lun y Vie
ZONA METRO,32440,OURENSE,1,Lun y Vie
ZONA METRO,32448,NOGUEIRA DE RAMUIN,1,Lun y Vie
ZONA METRO,32454,CENLLE - OURENSE,1,Lun y Vie
ZONA METRO,32456,OURENSE,1,Lun y Vie
ZONA METRO,32520,OURENSE,1,Lun y Vie
ZONA METRO,32539,OURENSE,1,Lun y Vie
ZONA METRO,32573,OURENSE,1,Lun y Vie
ZONA METRO,32613,OIMBRA - SAN CIBRAO,1,Lun y Vie
ZONA METRO,32625,OURENSE,1,Lun y Vie
ZONA METRO,32643,OURENSE,1,Lun y Vie
ZONA METRO,32650,OURENSE,1,Lun y Vie
ZONA METRO,32651,OURENSE,1,Lun y Vie
ZONA METRO,32652,OURENSE,1,Lun y Vie
ZONA METRO,32660,OURENSE,1,Lun y Vie
ZONA METRO,32670,OURENSE,1,Lun y Vie
ZONA METRO,32695,OURENSE,1,Lun y Vie
ZONA METRO,32698,OURENSE,1,Lun y Vie
ZONA METRO,32701,"BAÑOS DE MOLGAS, OURENSE",1,Lun y Vie
ZONA METRO,32701,BAÑOS DE MOLGAS-OURENSE,1,Lun y Vie
ZONA METRO,32702,OURENSE,1,Lun y Vie
ZONA METRO,32704,OURENSE,1,Lun y Vie
ZONA METRO,32710,CORTIÑA PEREIRO DE AGUIAR,1,Lun y Vie
ZONA METRO,32710,OURENSE,1,Lun y Vie
ZONA METRO,32710,PEREIRO DE AGUAR,1,Lun y Vie
ZONA METRO,32710,PEREIRO DE AGUIAR - OURENSE,1,Lun y Vie
ZONA METRO,32710,PEREIRO DE GUIAR1,1,Lun y Vie
ZONA METRO,32711,CONCELLO DE PEREIRO DE AGUIAR,1,Lun y Vie
ZONA METRO,32711,OURENSE,1,Lun y Vie
ZONA METRO,32720,OURENSE,1,Lun y Vie
ZONA METRO,32730,OURENSE,1,Lun y Vie
ZONA METRO,32748,OURENSE,1,Lun y Vie
ZONA METRO,32764,OURENSE,1,Lun y Vie
ZONA METRO,32780,A POBRA DE TRIVES ( OURENSE),1,Lun y Vie
ZONA METRO,32791,PEREIRO DE AGUIAR,1,Lun y Vie
ZONA METRO,32792,PEREIRO DE AGUIAR (OS GOZOS),1,Lun y Vie
ZONA METRO,32792,SANTA MARTA DE MOREIRAS PEREIRO DE AGUIA,1,Lun y Vie
ZONA METRO,32793,AYUNTAMIENTO DE PEREIRO DE AGUIAR,1,Lun y Vie
ZONA METRO,32793,O PEREIRO DE AGUIAR,1,Lun y Vie
ZONA METRO,32793,TAPADA DE BOUZAS-PEREIRO DE AGUIAR,1,Lun y Vie
ZONA METRO,32794,OURENSE,1,Lun y Vie
ZONA METRO,32812,OURENSE,1,Lun y Vie
ZONA METRO,32813,OURENSE,1,Lun y Vie
ZONA METRO,32814,QUINTELA  DE LEIRADO - OURENSE,1,Lun y Vie
ZONA METRO,32817,OURENSE,1,Lun y Vie
ZONA METRO,32823,OURENSE,1,Lun y Vie
ZONA METRO,32825,OURENSE,1,Lun y Vie
ZONA METRO,32826,OURENSE,1,Lun y Vie
ZONA METRO,32830,FORXAS DAS VIÑAS A MERCA,1,Lun y Vie
ZONA METRO,32830,OURENSE,1,Lun y Vie
ZONA METRO,32838,"SAN PEDRO DA MEZQUITA, A MERCA",1,Lun y Vie
ZONA METRO,32839,A MERCA,1,Lun y Vie
ZONA METRO,32839,ZARRACOS - A MERCA,1,Lun y Vie
ZONA METRO,32840,OURENSE,1,Lun y Vie
ZONA METRO,32890,LA VALENZANA - BARBADAS - OURENSE,1,Lun y Vie
ZONA METRO,32900,POLÍGONO SAN CIBRAO DAS VIÑAS,1,Lun y Vie
ZONA METRO,32900,SAN CIBRAN DAS VINHAS-OURENSE,1,Lun y Vie
ZONA METRO,32900,SAN CIBRAO DAS VIÑAS,1,Lun y Vie
ZONA METRO,32901,OURENSE,1,Lun y Vie
ZONA METRO,32901,SAN CIBRAO DAS VIÑAS,1,Lun y Vie
ZONA METRO,32910,SAN CIBRAO,1,Lun y Vie
ZONA METRO,32911,O PICOUTO SAN CIBRAO,1,Lun y Vie
ZONA METRO,32911,O PIÑEIRAL SAN CIBRAO,1,Lun y Vie
ZONA METRO,32911,OURENSE,1,Lun y Vie
ZONA METRO,32911,SAN CIBRAO,1,Lun y Vie
ZONA METRO,32911,SAN CIBRAO DAS VINAS,1,Lun y Vie
ZONA METRO,32915,OURENSE,1,Lun y Vie
ZONA METRO,32915,SAN CIBRAO DAS VIÑAS,1,Lun y Vie
ZONA METRO,32930,MUGARES TOEN,1,Lun y Vie
ZONA METRO,32930,SANTA MARIA DE XESTOSA (TOEN),1,Lun y Vie
ZONA METRO,32930,XESTOSA TOEN,1,Lun y Vie
ZONA METRO,32940,CONCELLO DE TOEN,1,Lun y Vie
ZONA METRO,32940,OURENSE,1,Lun y Vie
ZONA METRO,32940,"PUGA,TOEN",1,Lun y Vie
ZONA METRO,32940,TOEN,1,Lun y Vie
ZONA METRO,32960,OURENSE,1,Lun y Vie
ZONA METRO,32960,OURENSE A PEDRA,1,Lun y Vie
ZONA METRO,32980,"PARROQUÍA CASTRO DE BEIRO, OURENSE",1,Lun y Vie
ZONA METRO,32980,VENDANOVA -AMOEIRO,1,Lun y Vie
ZONA METRO,32981,BEIRO-OURENSE,1,Lun y Vie
ZONA METRO,32990,OURENSE,1,Lun y Vie"""

# --- 1. INICIALIZAR MEMORIA ---
if 'target_coords' not in st.session_state: st.session_state['target_coords'] = None
if 'target_name' not in st.session_state: st.session_state['target_name'] = ""
if 'km_result' not in st.session_state: st.session_state['km_result'] = 0
if 'tipo_calculo' not in st.session_state: st.session_state['tipo_calculo'] = "" 
if 'zona_info' not in st.session_state: st.session_state['zona_info'] = None
if 'logistica_transporte' not in st.session_state: st.session_state['logistica_transporte'] = ""
if 'logistica_frecuencia' not in st.session_state: st.session_state['logistica_frecuencia'] = ""
if 'logistica_acarreo' not in st.session_state: st.session_state['logistica_acarreo'] = ""
if 'historial_ruta' not in st.session_state: st.session_state['historial_ruta'] = ""
if 'tipo_transporte_seleccionado' not in st.session_state: st.session_state['tipo_transporte_seleccionado'] = ""
if 'encontrado_en_historial' not in st.session_state: st.session_state['encontrado_en_historial'] = False

# --- 2. CARGAR HISTORIAL ---
@st.cache_data
def cargar_historial():
    try:
        # Importante: Cierre de comillas arriba verificado
        df = pd.read_csv(io.StringIO(CSV_DATA), dtype={'Código postal envío': str})
        df['Ciudad_Clean'] = df['Ciudad_Clean'].astype(str).str.strip().str.upper()
        # ORDENAR POR FRECUENCIA: Así los destinos con más pedidos salen primero
        if 'Num_Pedidos_Historico' in df.columns:
            df = df.sort_values(by='Num_Pedidos_Historico', ascending=False)
        return df
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
        return None

df_historial = cargar_historial()
origen_ourense = (42.3358, -7.8639)

# --- 3. FUNCIONES DE CÁLCULO ---
def obtener_distancia_carretera(origen, destino):
    # 1. Calculamos SIEMPRE la lineal primero como seguro de vida
    dist_lineal = round(geodesic(origen, destino).km, 2)
    
    # 2. Intentamos la de carretera
    url = f"http://router.project-osrm.org/route/v1/driving/{origen[1]},{origen[0]};{destino[1]},{destino[0]}?overview=false"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if 'routes' in data and len(data['routes']) > 0:
                return round(data['routes'][0]['distance'] / 1000, 2), "🚗 Por Carretera"
    except:
        pass
    
    # 3. Si falla la carretera (o el server), devolvemos la lineal
    return dist_lineal, "✈️ Línea Recta (Backup)"

def calcular_logistica_completa(cp_detectado, nombre_busqueda=""):
    cp = str(cp_detectado).strip()
    nombre_busqueda = nombre_busqueda.strip().upper()
    
    # 1. BUSCAR EN HISTORIAL
    if df_historial is not None:
        match = df_historial[df_historial['Código postal envío'] == cp]
        if match.empty and nombre_busqueda:
             match = df_historial[df_historial['Ciudad_Clean'].str.contains(nombre_busqueda, na=False)]

        if not match.empty:
            # Como ya ordenamos el DataFrame al cargarlo, el primer resultado (iloc[0])
            # será siempre el destino más frecuente (el "bueno").
            dia = match.iloc[0]['Dia_Asignado']
            ruta = match.iloc[0]['Ruta_Asignada']
            st.session_state['encontrado_en_historial'] = True
            return "🚛 Transportes Martins", f"📅 {dia}", f"📍 Ruta: {ruta}"

    # 2. LOGICA GENERAL
    st.session_state['encontrado_en_historial'] = False
    if not cp or not cp[0].isdigit(): return "❓ Consultar", "Depende destino", "❓"
    
    if cp.startswith("32"): return "🚛 Flota Propia / Martins", "⚡ Diaria", "❌ No"
    elif cp.startswith("36"): return "🚚 Agencia Externa", "📅 L-X-V", "⚠️ Sí (Zona Acarreo)"
    else: return "✈️ Red Nacional", "⏱️ 48/72h", "⚠️ Sí"

def buscar_con_reintentos(query_dict_or_str, intentos=2):
    # Primero buscamos en la base de datos interna (BACKUP)
    if isinstance(query_dict_or_str, dict) and "postalcode" in query_dict_or_str:
        cp_backup = query_dict_or_str["postalcode"]
        if cp_backup in COORDENADAS_FIJAS:
            return type('obj', (object,), {'latitude': COORDENADAS_FIJAS[cp_backup][0], 'longitude': COORDENADAS_FIJAS[cp_backup][1], 'address': f"CP {cp_backup} (Interno)"})
    
    # Si no está en el backup, vamos a internet
    user_agent_unico = f"app_logistica_pro_{int(time.time())}_{random.randint(1,1000)}"
    geolocator = Nominatim(user_agent=user_agent_unico)
    
    for i in range(intentos):
        try:
            if i > 0: time.sleep(1.5)
            if isinstance(query_dict_or_str, dict):
                return geolocator.geocode(query_dict_or_str, timeout=10)
            else:
                return geolocator.geocode(query_dict_or_str, timeout=10)
        except: continue
    return None

# --- 4. INTERFAZ ---
col_izq, col_der = st.columns([1, 2])

with col_izq:
    st.subheader("📍 Datos del Envío")
    entrada = st.text_input("Destino (CP, Pueblo...):", placeholder="Ej: 27400 o Monforte")
    tipo_camion = st.selectbox("Selecciona Tipo Transporte:", ["ACARREO", "GRUA", "PEQUEÑO", "TRAILER"])
    btn_calc = st.button("🔍 Calcular Ruta", type="primary")

    if btn_calc and entrada:
        st.session_state['tipo_transporte_seleccionado'] = tipo_camion
        
        with st.spinner("Analizando datos..."):
            target_coords, target_name, cp_final = None, "", ""
            
            # 1. BUSCAR EN HISTORIAL
            historial_match = pd.DataFrame()
            if df_historial is not None:
                if entrada.isdigit():
                    historial_match = df_historial[df_historial['Código postal envío'] == entrada]
                else:
                    historial_match = df_historial[df_historial['Ciudad_Clean'].str.contains(entrada.strip().upper(), na=False)]
            
            if not historial_match.empty:
                # Cogemos el primer resultado (que ahora será el más frecuente gracias a la ordenación)
                cp_final = str(historial_match.iloc[0]['Código postal envío'])
                target_name = str(historial_match.iloc[0]['Ciudad_Clean'])
            else:
                if entrada.isdigit() and len(entrada) == 5: cp_final = entrada
            
            t, f, a = calcular_logistica_completa(cp_final, nombre_busqueda=entrada)
            
            # ----------------------------------------------------
            #  LÓGICA DE VEHÍCULOS (OVERRIDES) - JERARQUÍA
            # ----------------------------------------------------
            if tipo_camion == "TRAILER":
                t = "🚛 Transportes Ciquillo"
                # Mantenemos frecuencia calculada
            elif tipo_camion == "ACARREO":
                t = "🚛 Martins Dedicado"
                f = "📅 Diaria (250km/día)"
            # ----------------------------------------------------

            # 2. MAPA (INTENTO REFORZADO CON BACKUP INTERNO)
            loc = None
            if cp_final:
                loc = buscar_con_reintentos({"postalcode": cp_final, "country": "Spain"})
            
            if not loc:
                # Si falló por CP, intentamos por nombre libre
                loc = buscar_con_reintentos(f"{entrada}, España")
                if not loc: 
                    # Intento reforzado: Nombre + Provincia (ayuda mucho a desbloquear)
                    loc = buscar_con_reintentos(f"{entrada}, Pontevedra, España") # Por si es Lalin
                    if not loc:
                        loc = buscar_con_reintentos(f"{entrada}, Ourense, España")

            if loc:
                target_coords = (loc.latitude, loc.longitude)
                if not target_name: 
                    # Si viene de objeto geopy real tiene address
                    if hasattr(loc, 'address'):
                        target_name = loc.address.split(",")[0]
                    else:
                        target_name = f"Ubicación CP {cp_final}" # Viene del backup interno

                km, tipo_calc = obtener_distancia_carretera(origen_ourense, target_coords)
                
                if km <= 20: zona_res = ("ZONA 1 (0-20km)", "#FFF9C4")
                elif km <= 50: zona_res = ("ZONA 2 (20-50km)", "#FFCCBC")
                elif km <= 100: zona_res = ("ZONA 3 (50-100km)", "#B3E5FC")
                else: zona_res = ("ZONA 4 (>100km)", "#C8E6C9")
            else:
                km, tipo_calc = 0, "⚠️ Mapa no disponible"
                zona_res = ("Ubicación desconocida", "#E0E0E0")
                if not target_name: target_name = entrada

            st.session_state.update({
                'target_coords': target_coords, 'target_name': target_name,
                'km_result': km, 'tipo_calculo': tipo_calc, 'zona_info': zona_res,
                'logistica_transporte': t, 'logistica_frecuencia': f, 'logistica_acarreo': a
            })

    if st.session_state['logistica_transporte']:
        zona_txt, bg_color = st.session_state['zona_info'] if st.session_state['zona_info'] else ("-", "#fff")
        
        st.markdown(f"""
        <div style='background-color: {bg_color}; padding: 15px; border-radius: 10px; border: 1px solid #ccc; color: black;'>
            <h3 style='margin-top:0;'>{st.session_state['target_name']}</h3>
            <table style='width:100%'>
                <tr><td>🛣️ <strong>Distancia:</strong></td><td>{st.session_state['km_result']} km <small>({st.session_state['tipo_calculo']})</small></td></tr>
                <tr><td>📍 <strong>Zona:</strong></td><td>{zona_txt}</td></tr>
                <tr><td colspan="2"><hr></td></tr>
                <tr><td>🚛 <strong>Agencia:</strong></td><td><strong>{st.session_state['logistica_transporte']}</strong></td></tr>
                <tr><td>📅 <strong>Frecuencia:</strong></td><td>{st.session_state['logistica_frecuencia']}</td></tr>
                <tr><td>ℹ️ <strong>Ruta:</strong></td><td>{st.session_state['logistica_acarreo']}</td></tr>
                <tr><td colspan="2"><hr></td></tr>
                <tr><td>🏗️ <strong>Vehículo:</strong></td><td><strong>{st.session_state['tipo_transporte_seleccionado']}</strong></td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        # Alerta específica para TRAILER
        if st.session_state['tipo_transporte_seleccionado'] == "TRAILER":
            st.error("🚨 ATENCIÓN: Poner mensaje interno en PYXIS: Llamar a Ciquillo 48 horas antes")
        
        # NUEVA ALERTA PARA ACARREO
        if st.session_state['tipo_transporte_seleccionado'] == "ACARREO":
            st.warning("⚠️ ALERTA ACARREO: Preguntar al cliente qué tipo de acarreo quiere para ver si es viable o no.")

with col_der:
    st.subheader("🗺️ Zonas de Reparto")
    m = folium.Map(location=origen_ourense, zoom_start=9)
    
    EJES_CONFIG = {
        "EJE NORTE": {"coords": [42.4300, -8.0700], "color": "blue", "freq": "Martes", "radius": 15000},
        "EJE NORTE (Lalín)": {"coords": [42.6617, -8.1132], "color": "blue", "freq": "Martes", "radius": 12000},
        "EJE SUR (Xinzo)": {"coords": [42.0634, -7.7257], "color": "red", "freq": "Miércoles", "radius": 15000},
        "EJE SUR (Verín)": {"coords": [41.9366, -7.4393], "color": "red", "freq": "Miércoles", "radius": 12000},
        "EJE ESTE (Monforte)": {"coords": [42.5218, -7.5144], "color": "green", "freq": "Jueves", "radius": 15000},
        "EJE ESTE (Barco)": {"coords": [42.4168, -6.9839], "color": "green", "freq": "Jueves", "radius": 15000},
        "ZONA METRO": {"coords": [42.3358, -7.8639], "color": "purple", "freq": "Lun/Vie", "radius": 9000}
    }
    
    for nombre, config in EJES_CONFIG.items():
        folium.Circle(
            location=config["coords"],
            radius=config["radius"],
            color=config["color"],
            fill=True,
            fill_opacity=0.15,
            popup=f"<b>{nombre}</b><br>{config['freq']}"
        ).add_to(m)

    legend_html = '''
     <div style="position: fixed; top: 10px; right: 10px; width: 160px; height: 130px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; opacity: 0.9; padding: 10px; border-radius: 5px;">
     <b>Leyenda Rutas</b><br>
     <span style="color:purple;">●</span> Metro (Lun/Vie)<br>
     <span style="color:blue;">●</span> Norte (Martes)<br>
     <span style="color:red;">●</span> Sur (Miérc)<br>
     <span style="color:green;">●</span> Este (Jueves)<br>
     </div>
     '''
    m.get_root().html.add_child(folium.Element(legend_html))

    if st.session_state['target_coords']:
        target = st.session_state['target_coords']
        folium.Marker(target, popup="DESTINO", icon=folium.Icon(color="green", icon="flag")).add_to(m)
        folium.PolyLine([origen_ourense, target], color="black", weight=3).add_to(m)

    st_folium(m, width="100%", height=600)
