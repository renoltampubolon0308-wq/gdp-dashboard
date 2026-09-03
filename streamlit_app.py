import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd
import os
import utils

st.set_page_config(page_title="Dashboard Potensi Lokasi Ritel", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1f2937; padding: 12px; border-radius: 8px; border-left: 4px solid #3b82f6; }
    </style>
""", unsafe_allow_html=True)

# Default Titik Koordinat (Sukarame, Bandar Lampung)
if 'lat_click' not in st.session_state:
    st.session_state['lat_click'] = -5.394539
if 'lng_click' not in st.session_state:
    st.session_state['lng_click'] = 105.246964

# ==========================================
# 1. SIDEBAR UPLOAD & PARAMETER
# ==========================================
with st.sidebar:
    st.title("1. Upload Layer KML Internal")
    file_admin = st.file_uploader("Upload Batas Wilayah (KML/KMZ)", type=['kml', 'kmz'])
    file_eksis = st.file_uploader("Upload Toko Eksisting (KML/KMZ)", type=['kml', 'kmz'])
    file_komp = st.file_uploader("Upload Toko Kompetitor (KML/KMZ)", type=['kml', 'kmz'])
    
    st.divider()
    st.title("2. Parameter Buffer")
    radius_m = st.slider("Radius Analisis (meter):", min_value=100, max_value=1000, value=400, step=50)

# Load Layer
gdf_admin = utils.load_kml_kmz(file_admin)
gdf_eksis = utils.load_kml_kmz(file_eksis)
gdf_komp = utils.load_kml_kmz(file_komp)

# Tampilkan Notifikasi Status Upload di Sidebar
with st.sidebar:
    st.divider()
    st.write("📊 **Status File Loaded:**")
    if file_admin:
        if gdf_admin is not None:
            st.success(f"✅ Batas Wilayah: {len(gdf_admin)} Fitur")
        else:
            st.error("❌ Batas Wilayah: Gagal/Kosong")
            
    if file_eksis:
        if gdf_eksis is not None:
            st.success(f"✅ Toko Eksis: {len(gdf_eksis)} Titik")
        else:
            st.error("❌ Toko Eksis: Gagal/Kosong")
            
    if file_komp:
        if gdf_komp is not None:
            st.success(f"✅ Kompetitor: {len(gdf_komp)} Titik")
        else:
            st.error("❌ Kompetitor: Gagal/Kosong")

# Dataset lokal untuk skoring
@st.cache_data
def load_data_lokal():
    path_bng = "data/google_buildings.parquet"
    path_fasum = "data/fasum_faskom.parquet"
    gdf_bng = gpd.read_parquet(path_bng) if os.path.exists(path_bng) else None
    gdf_fasum = gpd.read_parquet(path_fasum) if os.path.exists(path_fasum) else None
    return gdf_bng, gdf_fasum

gdf_bng_lokal, gdf_fasum_lokal = load_data_lokal()

# Hitung Skor
res = utils.kalkulasi_skor_potensi(
    st.session_state['lat_click'], 
    st.session_state['lng_click'], 
    radius_m, 
    gdf_eksis=gdf_eksis, 
    gdf_komp=gdf_komp,
    gdf_bng=gdf_bng_lokal,
    gdf_fasum=gdf_fasum_lokal
)

# ==========================================
# 2. TOP KPI CARDS
# ==========================================
st.title("🏬 Dashboard Penilaian Potensi Lokasi")

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
    st.metric("SPD ESTIMATION", "Rp 12.5M", delta="Validasi Market", delta_color="off")

st.divider()

# ==========================================
# 3. PETA GOOGLE HYBRID & PANEL ANALISIS
# ==========================================
map_col, analysis_col = st.columns([6, 4])

with map_col:
    st.subheader("🗺️ Peta Google Maps Hybrid (Satelit + Label)")
    
    m = folium.Map(
        location=[st.session_state['lat_click'], st.session_state['lng_click']], 
        zoom_start=15,
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='Google Maps Hybrid'
    )
    
    all_bounds = []

    # 1. RENDER BATAS WILAYAH (ADM)
    if gdf_admin is not None and not gdf_admin.empty:
        folium.GeoJson(
            gdf_admin,
            name="Batas Wilayah (ADM)",
            style_function=lambda x: {
                'fillColor': '#f59e0b', 
                'color': '#d97706', 
                'weight': 3, 
                'fillOpacity': 0.35
            },
            tooltip=folium.GeoJsonTooltip(fields=['Name'] if 'Name' in gdf_admin.columns else [], labels=False)
        ).add_to(m)
        
        # Ambil Bounding Box ADM
        minx, miny, maxx, maxy = gdf_admin.total_bounds
        all_bounds.append([[miny, minx], [maxy, maxx]])

    # 2. RENDER TOKO EKSISTING (PIN BIRU)
    if gdf_eksis is not None and not gdf_eksis.empty:
        for idx, row in gdf_eksis.iterrows():
            if row.geometry is not None:
                pt = row.geometry if row.geometry.geom_type == 'Point' else row.geometry.centroid
                nama = row.get('Name') or f"Toko Eksis #{idx+1}"
                folium.Marker(
                    location=[pt.y, pt.x],
                    popup=f"<b>Toko Eksisting:</b><br>{nama}",
                    icon=folium.Icon(color="blue", icon="shopping-bag", prefix="fa")
                ).add_to(m)

    # 3. RENDER TOKO KOMPETITOR (PIN ORANYE)
    if gdf_komp is not None and not gdf_komp.empty:
        for idx, row in gdf_komp.iterrows():
            if row.geometry is not None:
                pt = row.geometry if row.geometry.geom_type == 'Point' else row.geometry.centroid
                nama = row.get('Name') or f"Kompetitor #{idx+1}"
                folium.Marker(
                    location=[pt.y, pt.x],
                    popup=f"<b>Kompetitor:</b><br>{nama}",
                    icon=folium.Icon(color="orange", icon="store", prefix="fa")
                ).add_to(m)

    # Titik Analisis Utama & Buffer Radius
    folium.Marker(
        [st.session_state['lat_click'], st.session_state['lng_click']],
        popup="Calon Lokasi Toko",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)
    
    folium.Circle(
        radius=radius_m,
        location=[st.session_state['lat_click'], st.session_state['lng_click']],
        color="#8b5cf6",
        fill=True,
        fill_opacity=0.25,
        popup=f"Area Radius {radius_m}m"
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    # Otomatis Zoom ke Area Layer jika Ada
    if all_bounds:
        m.fit_bounds(all_bounds[0])
    
    map_data = st_folium(m, width="100%", height=520)
    
    if map_data and map_data.get("last_clicked"):
        st.session_state['lat_click'] = map_data["last_clicked"]["lat"]
        st.session_state['lng_click'] = map_data["last_clicked"]["lng"]

with analysis_col:
    st.subheader("📍 ANALISIS LOKASI POTENSI")
    st.caption("Koordinat Titik Terpilih:")
    st.code(f"{st.session_state['lat_click']:.6f}, {st.session_state['lng_click']:.6f}", language="text")
    
    skor = res['skor_total']
    if skor >= 80:
        st.success(f"### ⭐ SANGAT POTENSIAL (Skor: {skor} / 100)")
    elif skor >= 60:
        st.warning(f"### 🟡 POTENSIAL (Skor: {skor} / 100)")
    else:
        st.error(f"### 🔴 KURANG POTENSIAL (Skor: {skor} / 100)")
        
    st.markdown("**Faktor Penilaian:**")
    st.caption("🏠 Kepadatan Bangunan (Google Open Buildings)")
    st.progress(res['skor_bng'] / 25, text=f"{res['skor_bng']} / 25 ({res['kat_bng']})")
    
    st.caption("🛒 Money Traffic (Fasum/Faskom Auto-Fetch)")
    st.progress(res['skor_fasum'] / 30, text=f"{res['skor_fasum']} / 30 ({res['detail_fasum']})")
    
    st.caption("💰 Validasi Market Volume (SPD)")
    st.progress(res['skor_spd'] / 25, text=f"{res['skor_spd']} / 25")
    
    st.caption("🛣️ Akses Jalan")
    st.progress(res['skor_jalan'] / 20, text=f"{res['skor_jalan']} / 20 (Jalan Kolektor)")
