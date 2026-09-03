import streamlit as st
import folium
from streamlit_folium import st_folium
import utils

# Config Halaman
st.set_page_config(page_title="Dashboard Potensi Lokasi Ritel", layout="wide")

# Custom Styling biar UI Clean & Modern
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 12px; border-radius: 8px; border-left: 4px solid #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'lat_click' not in st.session_state:
    st.session_state['lat_click'] = -5.381234
if 'lng_click' not in st.session_state:
    st.session_state['lng_click'] = 105.289012

# ==========================================
# 1. SIDEBAR (SISI KIRI) - INPUT DATA & PARAMETER
# ==========================================
with st.sidebar:
    st.title("📂 Input Data KML/KMZ")
    file_admin = st.file_uploader("Upload Batas Wilayah", type=['kml', 'kmz'])
    file_eksis = st.file_uploader("Upload Toko Eksisting & SPD", type=['kml', 'kmz'])
    file_komp = st.file_uploader("Upload Toko Kompetitor & SPD", type=['kml', 'kmz'])
    file_fasum = st.file_uploader("Upload Fasum / Faskom", type=['kml', 'kmz'])
    
    st.divider()
    st.header("⚙️ Parameter Buffer")
    radius_m = st.slider("Radius Analisis (meter):", min_value=100, max_value=1000, value=400, step=50)
    
    btn_analisis = st.button("🔍 JALANKAN ANALISIS", type="primary", use_container_width=True)

# Load Layer
gdf_admin = utils.load_kml_kmz(file_admin)
gdf_eksis = utils.load_kml_kmz(file_eksis)
gdf_komp = utils.load_kml_kmz(file_komp)
gdf_fasum = utils.load_kml_kmz(file_fasum)

# Hitung Hasil Analisis untuk Titik Terpilih
res = utils.kalkulasi_skor_potensi(
    st.session_state['lat_click'], 
    st.session_state['lng_click'], 
    radius_m, 
    None,  # Layer Google Buildings (dapat dihubungkan ke geoparquet/KML)
    gdf_eksis, 
    gdf_komp, 
    gdf_fasum
)

# ==========================================
# 2. TOP BAR: 5 KPI CARDS
# ==========================================
st.title("🏬 Dashboard Penilaian Potensi Lokasi Ritel")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

with kpi1:
    st.metric("SKOR POTENSI", f"{res['skor_total']} / 100", 
              delta="Sangat Potensial" if res['skor_total']>=80 else ("Potensial" if res['skor_total']>=60 else "Kurang Potensial"))
with kpi2:
    st.metric("BANGUNAN (GOOGLE)", f"{res['total_bng']} Unit", delta=f"{res['kepadatan_ha']} bng/ha ({res['kat_bng']})", delta_color="off")
with kpi3:
    st.metric("FASUM / FASKOM", f"{res['fasum_count']} Titik", delta=res['detail_fasum'])
with kpi4:
    st.metric("TOKO / KOMPETITOR", f"{res['count_eksis']} / {res['count_komp']}", delta="Unit Terdeteksi", delta_color="off")
with kpi5:
    spd_eksis_txt = f"Rp {res['spd_eksis_val']/1e6:.1f}M" if res['spd_eksis_val']>=1e6 else "Rp 0"
    spd_komp_txt = f"Rp {res['spd_komp_val']/1e6:.1f}M" if res['spd_komp_val']>=1e6 else "Rp 0"
    st.metric("SPD COMPARISON", spd_eksis_txt, delta=f"Pesaing: {spd_komp_txt}", delta_color="inverse")

st.divider()

# ==========================================
# 3. MAIN AREA: PETA & PANEL ANALISIS
# ==========================================
map_col, analysis_col = st.columns([6, 4])

# --- SISI KIRI: PETA INTERAKTIF ---
with map_col:
    st.subheader("🗺️ Peta Persebaran Spasial")
    
    m = folium.Map(location=[st.session_state['lat_click'], st.session_state['lng_click']], zoom_start=15)
    
    # Tambahkan Marker & Buffer Circle
    folium.Marker(
        [st.session_state['lat_click'], st.session_state['lng_click']],
        popup="Calon Lokasi Toko",
        icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa")
    ).add_to(m)
    
    folium.Circle(
        radius=radius_m,
        location=[st.session_state['lat_click'], st.session_state['lng_click']],
        color="#8b5cf6",
        fill=True,
        fill_opacity=0.2,
        popup=f"Area Radius {radius_m}m"
    ).add_to(m)
    
    # Catch Event Klik Peta
    map_data = st_folium(m, width="100%", height=520)
    
    if map_data and map_data.get("last_clicked"):
        st.session_state['lat_click'] = map_data["last_clicked"]["lat"]
        st.session_state['lng_click'] = map_data["last_clicked"]["lng"]

# --- SISI KANAN: PANEL ANALISIS LOKASI POTENSI ---
with analysis_col:
    st.subheader("📍 ANALISIS LOKASI POTENSI")
    
    # Salin Koordinat Cepat
    st.caption("Koordinat Titik Terpilih:")
    st.code(f"{st.session_state['lat_click']:.6f}, {st.session_state['lng_click']:.6f}", language="text")
    
    # Status Badge
    skor = res['skor_total']
    if skor >= 80:
        st.success(f"### ⭐ SANGAT POTENSIAL (Skor: {skor} / 100)")
        st.caption("Lokasi ini sangat direkomendasikan untuk pembukaan toko baru.")
    elif skor >= 60:
        st.warning(f"### 🟡 POTENSIAL (Skor: {skor} / 100)")
        st.caption("Lokasi memadai, disarankan lanjut survei lapangan.")
    else:
        st.error(f"### 🔴 KURANG POTENSIAL (Skor: {skor} / 100)")
        st.caption("Resiko tinggi, kepadatan/money traffic kurang mendukung.")
        
    st.markdown("**Faktor Penilaian:**")
    
    st.caption("🏠 Kepadatan Bangunan")
    st.progress(res['skor_bng'] / 25, text=f"{res['skor_bng']} / 25 ({res['kat_bng']})")
    
    st.caption("🛒 Money Traffic (Fasum/Pasar)")
    st.progress(res['skor_fasum'] / 30, text=f"{res['skor_fasum']} / 30 ({res['detail_fasum']})")
    
    st.caption("💰 Validasi Market Volume (SPD)")
    st.progress(res['skor_spd'] / 25, text=f"{res['skor_spd']} / 25")
    
    st.caption("🛣️ Akses Jalan")
    st.progress(res['skor_jalan'] / 20, text=f"{res['skor_jalan']} / 20 (Jalan Kolektor)")
    
    if res['penalti'] > 0:
        st.caption(f"⚠️ Penalti Kompetitor: -{res['penalti']} Poin ({res['count_komp']} toko pesaing)")
