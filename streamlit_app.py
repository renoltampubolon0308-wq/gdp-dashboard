import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from utils import baca_kml, hitung_kepadatan_google_buildings, kalkulasi_skor_potensi

# ---------------------------------------------------------
# 1. PAGE CONFIG & DARK THEME CUSTOM CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Penilaian Potensi Lokasi",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0f172a; color: #f8fafc; }
    [data-testid="stSidebar"] { background-color: #1e293b; border-right: 1px solid #334155; }
    .metric-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px; color: white; }
    .metric-title { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
    .metric-value { font-size: 1.75rem; font-weight: 700; }
    .metric-sub { font-size: 0.8rem; color: #94a3b8; margin-top: 4px; }
    .custom-card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. INISIALISASI SESSION STATE
# ---------------------------------------------------------
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -5.3850
if "selected_lng" not in st.session_state:
    st.session_state["selected_lng"] = 105.2990

# ---------------------------------------------------------
# 3. SIDEBAR
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

st.sidebar.markdown("---")
st.sidebar.caption("📍 **Koordinat Evaluasi Terpilih:**")
st.sidebar.code(f"Lat: {st.session_state['selected_lat']:.6f}\nLng: {st.session_state['selected_lng']:.6f}", language="text")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
btn_analisis = st.sidebar.button("► JALANKAN ANALISIS", use_container_width=True, type="primary")

st.sidebar.markdown("---")
st.sidebar.markdown("ℹ️ **Keterangan**")
st.sidebar.caption("Analisis menggunakan kepadatan bangunan Google Open Buildings serta data internal toko eksisting dan kompetitor.")

# BACA FILE KML
gdf_batas = baca_kml(file_batas) if file_batas else None
gdf_eksisting = baca_kml(file_toko_eksisting) if file_toko_eksisting else None
gdf_kompetitor = baca_kml(file_kompetitor) if file_kompetitor else None

n_eksisting = len(gdf_eksisting) if gdf_eksisting is not None else 0
n_kompetitor = len(gdf_kompetitor) if gdf_kompetitor is not None else 0

# HITUNG DENSITAS & SKOR
total_bangunan = hitung_kepadatan_google_buildings(st.session_state["selected_lat"], st.session_state["selected_lng"], radius_buffer)
skor_total, faktor = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)

# ---------------------------------------------------------
# 4. HEADER SECTION
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
# 5. TOP METRICS BAR
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
        <div class="metric-sub">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #a855f7;">TOKO EKSISTING</div>
        <div class="metric-value">{n_eksisting}</div>
        <div class="metric-sub">file ter-upload</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #f97316;">KOMPETITOR</div>
        <div class="metric-value">{n_kompetitor}</div>
        <div class="metric-sub">file ter-upload</div>
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
# 6. MIDDLE SECTION: PETA INTERAKTIF & HASIL ANALISIS
# ---------------------------------------------------------
c_map, c_analisis = st.columns([2.2, 1])

with c_map:
    st.subheader("Peta Persebaran Spasial")
    st.caption("💡 *Klik lokasi mana saja pada peta untuk memindahkan titik evaluasi.*")
    
    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        show_bg = st.checkbox("Bangunan", value=True)
    with f_col2:
        show_eks = st.checkbox("Toko Eksisting", value=True)
    with f_col3:
        show_komp = st.checkbox("Kompetitor", value=True)
    with f_col4:
        show_bts = st.checkbox("Batas Wilayah", value=True)

    # Inisialisasi Peta
    m = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]], 
        zoom_start=14, 
        tiles="OpenStreetMap"
    )

    # 1. Layer Batas Wilayah (GeoJson)
    if show_bts and gdf_batas is not None:
        folium.GeoJson(
            gdf_batas,
            style_function=lambda x: {'fillColor': '#3b82f6', 'color': '#2563eb', 'weight': 2, 'fillOpacity': 0.1}
        ).add_to(m)

    # 2. Layer Toko Eksisting (GeoJson langsung agar presisi & kompatibel dengan semua tipe geometri KML)
    if show_eks and gdf_eksisting is not None:
        folium.GeoJson(
            gdf_eksisting,
            name="Toko Eksisting",
            marker=folium.Marker(icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa")),
            tooltip=folium.GeoJsonTooltip(fields=[gdf_eksisting.columns[0]], aliases=["Nama Toko:"]) if len(gdf_eksisting.columns) > 0 else None
        ).add_to(m)

    # 3. Layer Kompetitor (GeoJson)
    if show_komp and gdf_kompetitor is not None:
        folium.GeoJson(
            gdf_kompetitor,
            name="Kompetitor",
            marker=folium.Marker(icon=folium.Icon(color="orange", icon="store", prefix="fa")),
            tooltip=folium.GeoJsonTooltip(fields=[gdf_kompetitor.columns[0]], aliases=["Kompetitor:"]) if len(gdf_kompetitor.columns) > 0 else None
        ).add_to(m)

    # 4. Marker Titik Evaluasi Terpilih
    folium.Marker(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        popup="Titik Evaluasi Terpilih",
        tooltip="Titik Evaluasi",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    # 5. Radius Buffer
    folium.Circle(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        radius=radius_buffer,
        color="#6366f1",
        weight=2,
        fill=True,
        fill_opacity=0.15
    ).add_to(m)

    # Render peta dengan menangkap respons klik secara mendalam
    map_data = st_folium(
        m, 
        width="100%", 
        height=480, 
        key="main_interactive_map",
        returned_objects=["last_clicked"]
    )

    # LOGIKA KLIK PETA
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lng = map_data["last_clicked"]["lng"]
        
        # Toleransi perubahan koordinat untuk pemicu rerun
        if abs(clicked_lat - st.session_state["selected_lat"]) > 0.00001 or abs(clicked_lng - st.session_state["selected_lng"]) > 0.00001:
            st.session_state["selected_lat"] = clicked_lat
            st.session_state["selected_lng"] = clicked_lng
            st.rerun()

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
# 7. BOTTOM SECTION: INSIGHT LOKASI & REKOMENDASI
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
            <div style="color: #94a3b8; font-size: 0.75rem;">{total_bangunan:,} bangunan dalam radius {radius_buffer/1000:.1f} km.</div>
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
            <div style="color: #94a3b8; font-size: 0.75rem;">{n_kompetitor} toko terdeteksi.</div>
        </div>
        """, unsafe_allow_html=True)

    with i4:
        st.markdown(f"""
        <div class="custom-card">
            <div style="color: #22c55e; font-size: 0.8rem; font-weight: bold;">Toko Eksisting</div>
            <div style="color: #22c55e; font-size: 1.1rem; font-weight: bold; margin: 4px 0;">ADA</div>
            <div style="color: #94a3b8; font-size: 0.75rem;">Terdapat {n_eksisting} toko eksisting di area ini.</div>
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
