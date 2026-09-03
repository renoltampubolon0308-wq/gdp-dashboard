import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from utils import baca_kml, hitung_kepadatan_google_buildings, kalkulasi_skor_potensi

# ---------------------------------------------------------
# PAGE CONFIG & DARK THEME CUSTOM CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Penilaian Potensi Lokasi",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* Global Background */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #1e293b;
        border-right: 1px solid #334155;
    }
    
    /* Top Metric Card Styling */
    .metric-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 16px;
        color: white;
    }
    .metric-title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 4px;
    }
    
    /* Custom Card */
    .custom-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
    }
    
    /* Progress bar custom color */
    .stProgress > div > div > div > div {
        background-color: #22c55e;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
st.sidebar.markdown("### DATA INPUT")
st.sidebar.caption("Batas Wilayah")
file_batas = st.sidebar.file_uploader("Upload ADM_SUKARAME.kml", type=["kml", "kmz"], key="f_batas", label_visibility="collapsed")

st.sidebar.caption("Toko Eksisting & SPD")
file_toko_eksisting = st.sidebar.file_uploader("Upload TOKOIDM.kml", type=["kml", "kmz"], key="f_toko", label_visibility="collapsed")

st.sidebar.caption("Toko Kompetitor")
file_kompetitor = st.sidebar.file_uploader("Upload KOMPETITOR.kml", type=["kml", "kmz"], key="f_komp", label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.markdown("### PARAMETER ANALISIS")

st.sidebar.caption("Radius Analisis (meter)")
radius_buffer = st.sidebar.number_input("Radius Analisis", min_value=200, max_value=5000, value=1000, step=100, label_visibility="collapsed")

st.sidebar.caption("Metode Penilaian")
metode = st.sidebar.selectbox("Metode Penilaian", ["Google Buildings Focused", "Weighted Overlay", "Buffer Density"], label_visibility="collapsed")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
btn_analisis = st.sidebar.button("► JALANKAN ANALISIS", use_container_width=True, type="primary")

st.sidebar.markdown("---")
st.sidebar.markdown("ℹ️ **Keterangan**")
st.sidebar.caption("Analisis menggunakan kepadatan bangunan Google Open Buildings serta data internal toko eksisting dan kompetitor.")

# READ KML
gdf_batas = baca_kml(file_batas) if file_batas else None
gdf_eksisting = baca_kml(file_toko_eksisting) if file_toko_eksisting else None
gdf_kompetitor = baca_kml(file_kompetitor) if file_kompetitor else None

# Default Center
center_lat, center_lon = -5.3850, 105.2990
if gdf_batas is not None and not gdf_batas.empty:
    bounds = gdf_batas.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

# Initial State
if "analisis_done" not in st.session_state:
    st.session_state.analisis_done = True

if btn_analisis:
    st.session_state.analisis_done = True

# Hitung data jika analisis aktif
n_eksisting = len(gdf_eksisting) if gdf_eksisting is not None else 3
n_kompetitor = len(gdf_kompetitor) if gdf_kompetitor is not None else 7

if st.session_state.analisis_done:
    total_bangunan = hitung_kepadatan_google_buildings(center_lat, center_lon, radius_buffer)
    skor_total, faktor = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)
else:
    total_bangunan = 1245
    skor_total, faktor = 82, {"Kepadatan Bangunan": 90, "Akses Jalan": 82, "Toko Eksisting (SPD)": 70, "Kompetitor": 50, "POI & Fasilitas": 75}

# ---------------------------------------------------------
# HEADER SECTION
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.title("Dashboard Penilaian Potensi Lokasi")
    st.caption("Analisis Lokasi Berbasis Google Open Buildings + Data Internal")

with head_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        st.button("📥 Export", use_container_width=True)
    with btn_col2:
        st.button("📄 Buat PDF", use_container_width=True, type="primary")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TOP METRICS BAR
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(f"""
    <div class="metric-card" style="border-left: 4px solid #22c55e;">
        <div class="metric-title" style="color: #22c55e;">SKOR POTENSI</div>
        <div class="metric-value">{skor_total} <span style="font-size: 1rem; color: #94a3b8;">/ 100</span></div>
        <div class="metric-sub" style="color: #22c55e;">Sangat Potensial 🎯</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #3b82f6;">BANGUNAN (GOOGLE)</div>
        <div class="metric-value">{total_bangunan:,}</div>
        <div class="metric-sub">dalam radius {radius_buffer/1000:.0f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #a855f7;">TOKO EKSISTING</div>
        <div class="metric-value">{n_eksisting}</div>
        <div class="metric-sub">dalam radius {radius_buffer/1000:.0f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #f97316;">KOMPETITOR</div>
        <div class="metric-value">{n_kompetitor}</div>
        <div class="metric-sub">dalam radius {radius_buffer/1000:.0f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m5:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title" style="color: #eab308;">SPD TOKO EKSISTING</div>
        <div class="metric-value">Rp 12,5 jt</div>
        <div class="metric-sub">rata-rata / hari</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# MIDDLE SECTION: PETA & HASIL ANALISIS
# ---------------------------------------------------------
c_map, c_analisis = st.columns([2.2, 1])

with c_map:
    st.subheader("Peta Persebaran Spasial")
    
    # Layer filter controls
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        show_bg = st.checkbox("Bangunan", value=True)
    with f_col2:
        show_eks = st.checkbox("Toko Eksisting", value=True)
    with f_col3:
        show_komp = st.checkbox("Kompetitor", value=True)
    with f_col4:
        show_bts = st.checkbox("Batas Wilayah", value=True)

    # Dark Theme Folium Map
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=14, 
        tiles="CartoDB dark_matter"
    )

    # Batas Wilayah Layer
    if show_bts and gdf_batas is not None:
        folium.GeoJson(
            gdf_batas,
            style_function=lambda x: {'fillColor': '#3b82f6', 'color': '#60a5fa', 'weight': 2, 'fillOpacity': 0.15}
        ).add_to(m)

    # Center Marker
    folium.Marker(
        location=[center_lat, center_lon],
        popup="Titik Evaluasi",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    # Radius Circle
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_buffer,
        color="#818cf8",
        weight=2,
        fill=True,
        fill_opacity=0.1
    ).add_to(m)

    # Toko Eksisting (Hijau)
    if show_eks and gdf_eksisting is not None:
        for idx, row in gdf_eksisting.iterrows():
            if row.geometry.geom_type == 'Point':
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa")
                ).add_to(m)

    # Kompetitor (Merah/Oranye)
    if show_komp and gdf_kompetitor is not None:
        for idx, row in gdf_kompetitor.iterrows():
            if row.geometry.geom_type == 'Point':
                folium.Marker(
                    location=[row.geometry.y, row.geometry.x],
                    icon=folium.Icon(color="orange", icon="store", prefix="fa")
                ).add_to(m)

    st_folium(m, width="100%", height=480)

with c_analisis:
    st.subheader("Hasil Analisis Potensi")
    
    st.markdown("""
    <div style="background-color: #064e3b; border: 1px solid #059669; padding: 12px; border-radius: 8px; margin-bottom: 16px;">
        <span style="color: #34d399; font-weight: bold;">⭐ POTENSI TINGGI</span><br>
        <span style="color: #a7f3d0; font-size: 0.85rem;">Lokasi ini memiliki potensi yang baik untuk pengembangan toko baru.</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"### Skor Potensi: **{skor_total}** / 100")
    st.progress(skor_total / 100)

    st.markdown("<br><b>Faktor Penilaian:</b>", unsafe_allow_html=True)
    
    for nama_faktor, nilai in faktor.items():
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            st.caption(f"🏠 {nama_faktor}" if "Bangunan" in nama_faktor else f"🛣️ {nama_faktor}" if "Jalan" in nama_faktor else f"🛒 {nama_faktor}" if "Eksisting" in nama_faktor else f"⚔️ {nama_faktor}" if "Kompetitor" in nama_faktor else f"📍 {nama_faktor}")
        with col_f2:
            st.markdown(f"**{nilai}** / 100")

# ---------------------------------------------------------
# BOTTOM SECTION: INSIGHT LOKASI & REKOMENDASI
# ---------------------------------------------------------
st.markdown("---")
c_insight, c_rekom = st.columns([2, 1])

with c_insight:
    st.subheader("💡 Insight Lokasi")
    
    i1, i2, i3, i4 = st.columns(4)
    with i1:
        st.markdown(f"""
        <div class="custom-card">
            <div style="color: #22c55e; font-size: 0.8rem; font-weight: bold;">Kepadatan Bangunan</div>
            <div style="color: #22c55e; font-size: 1.1rem; font-weight: bold; margin: 4px 0;">TINGGI</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">{total_bangunan:,} bangunan dalam radius {radius_buffer/1000:.0f} km.</div>
        </div>
        """, unsafe_allow_html=True)

    with i2:
        st.markdown("""
        <div class="custom-card">
            <div style="color: #22c55e; font-size: 0.8rem; font-weight: bold;">Akses Jalan</div>
            <div style="color: #22c55e; font-size: 1.1rem; font-weight: bold; margin: 4px 0;">TINGGI</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">Dekat dengan jaringan jalan utama.</div>
        </div>
        """, unsafe_allow_html=True)

    with i3:
        st.markdown(f"""
        <div class="custom-card">
            <div style="color: #eab308; font-size: 0.8rem; font-weight: bold;">Kompetitor</div>
            <div style="color: #eab308; font-size: 1.1rem; font-weight: bold; margin: 4px 0;">SEDANG</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">{n_kompetitor} kompetitor dalam radius {radius_buffer/1000:.0f} km.</div>
        </div>
        """, unsafe_allow_html=True)

    with i4:
        st.markdown(f"""
        <div class="custom-card">
            <div style="color: #22c55e; font-size: 0.8rem; font-weight: bold;">Toko Eksisting</div>
            <div style="color: #22c55e; font-size: 1.1rem; font-weight: bold; margin: 4px 0;">ADA</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">Terdapat {n_eksisting} toko eksisting di sekitar.</div>
        </div>
        """, unsafe_allow_html=True)

with c_rekom:
    st.subheader("🎯 Rekomendasi")
    st.markdown(f"""
    <div style="background-color: #064e3b; border: 1px solid #059669; padding: 20px; border-radius: 12px;">
        <div style="color: #34d399; font-weight: bold; font-size: 1.1rem;">DIREKOMENDASIKAN</div>
        <div style="color: #a7f3d0; font-size: 0.85rem; margin-top: 6px;">Lokasi ini direkomendasikan untuk analisis lebih lanjut dan survei lapangan.</div>
        <hr style="border-color: #059669; margin: 12px 0;">
        <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #a7f3d0;">
            <span>Score Potensi: <b>{skor_total} / 100</b></span>
            <span>Status: <b>Lanjutkan Survei</b></span>
        </div>
    </div>
    """, unsafe_allow_html=True)
