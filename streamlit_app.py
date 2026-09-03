import streamlit as st
import folium
from streamlit_folium import st_folium
from utils import (
    baca_kml, 
    hitung_fitur_dalam_radius, 
    hitung_kepadatan_google_buildings, 
    kalkulasi_skor_potensi
)

st.set_page_config(layout="wide", page_title="Dashboard Penilaian Potensi Lokasi")

# ---------------------------------------------------------
# 1. SESSION STATE INIT
# ---------------------------------------------------------
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -5.385561
if "selected_lng" not in st.session_state:
    st.session_state["selected_lng"] = 105.296134

# ---------------------------------------------------------
# 2. SIDEBAR - INPUT DATA
# ---------------------------------------------------------
st.sidebar.title("DATA INPUT")

file_batas = st.sidebar.file_uploader("Batas Wilayah (KML)", type=["kml"], key="batas")
file_toko_eksisting = st.sidebar.file_uploader("Toko Eksisting & SPD (KML)", type=["kml"], key="eksisting")
file_kompetitor = st.sidebar.file_uploader("Toko Kompetitor (KML)", type=["kml"], key="kompetitor")

st.sidebar.markdown("---")
st.sidebar.title("PARAMETER ANALISIS")
radius_buffer = st.sidebar.number_input("Radius Analisis (meter)", min_value=100, max_value=2000, value=400, step=100)
metode_penilaian = st.sidebar.selectbox("Metode Penilaian", ["Google Buildings Focused", "Weighted Overlay", "Buffer Density"])

# ---------------------------------------------------------
# 3. KML PROCESSING & RADIUS FILTERING
# ---------------------------------------------------------
gdf_batas = baca_kml(file_batas) if file_batas else None
gdf_eksisting_raw = baca_kml(file_toko_eksisting) if file_toko_eksisting else None
gdf_kompetitor_raw = baca_kml(file_kompetitor) if file_kompetitor else None

# Filter Fitur Hanya Dalam Radius Titik Terpilih
n_eksisting, gdf_eksisting_radius = hitung_fitur_dalam_radius(
    gdf_eksisting_raw, 
    st.session_state["selected_lat"], 
    st.session_state["selected_lng"], 
    radius_buffer
)

n_kompetitor, gdf_kompetitor_radius = hitung_fitur_dalam_radius(
    gdf_kompetitor_raw, 
    st.session_state["selected_lat"], 
    st.session_state["selected_lng"], 
    radius_buffer
)

# Hitung Rata-Rata SPD Terakhir (JUNI) dalam Radius
if gdf_eksisting_radius is not None and 'SPD_Terakhir_Val' in gdf_eksisting_radius.columns and n_eksisting > 0:
    avg_spd = gdf_eksisting_radius['SPD_Terakhir_Val'].mean()
    spd_text = f"Rp {avg_spd/1_000_000:.1f} jt"
else:
    spd_text = "Rp 0 jt"

# Total Bangunan & Skor
total_bangunan = hitung_kepadatan_google_buildings(
    st.session_state["selected_lat"], 
    st.session_state["selected_lng"], 
    radius_buffer
)
skor_total, faktor = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)

# ---------------------------------------------------------
# 4. HEADER SECTION (KOORDINAT CLEAN 1 BARIS)
# ---------------------------------------------------------
head_col1, head_col2 = st.columns([2.5, 1.5])

with head_col1:
    st.title("Dashboard Penilaian Potensi Lokasi")
    st.caption("Analisis Lokasi Berbasis Google Open Buildings + Data Internal")

with head_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    # Tampilan koordinat 1 baris murni
    koordinat_str = f"{st.session_state['selected_lat']:.6f}, {st.session_state['selected_lng']:.6f}"
    st.code(koordinat_str, language="text")

# ---------------------------------------------------------
# 5. METRICS BAR (DINAMIS DENGAN RADIUS)
# ---------------------------------------------------------
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #22c55e;">
        <div style="color: #94a3b8; font-size: 12px; font-weight: bold;">SKOR POTENSI</div>
        <div style="color: white; font-size: 28px; font-weight: bold;">{skor_total} <span style="font-size: 14px; color: #94a3b8;">/ 100</span></div>
        <div style="color: #22c55e; font-size: 12px;">Potensial</div>
    </div>
    """, unsafe_allow_html=True)

with m2:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px;">
        <div style="color: #94a3b8; font-size: 12px; font-weight: bold;">BANGUNAN (GOOGLE)</div>
        <div style="color: white; font-size: 28px; font-weight: bold;">{total_bangunan:,}</div>
        <div style="color: #94a3b8; font-size: 12px;">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m3:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px;">
        <div style="color: #a855f7; font-size: 12px; font-weight: bold;">TOKO EKSISTING</div>
        <div style="color: white; font-size: 28px; font-weight: bold;">{n_eksisting}</div>
        <div style="color: #94a3b8; font-size: 12px;">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m4:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px;">
        <div style="color: #f97316; font-size: 12px; font-weight: bold;">KOMPETITOR</div>
        <div style="color: white; font-size: 28px; font-weight: bold;">{n_kompetitor}</div>
        <div style="color: #94a3b8; font-size: 12px;">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with m5:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px;">
        <div style="color: #eab308; font-size: 12px; font-weight: bold;">SPD TOKO EKSISTING</div>
        <div style="color: white; font-size: 28px; font-weight: bold;">{spd_text}</div>
        <div style="color: #94a3b8; font-size: 12px;">rata-rata di radius ini</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. PETA INTERAKTIF SATELIT
# ---------------------------------------------------------
col_peta, col_info = st.columns([2, 1])

with col_peta:
    st.subheader("Peta Persebaran Spasial")
    st.caption("Click lokasi mana saja pada peta untuk memindahkan titik evaluasi.")

    # Peta Utama (Google Satelit Hybrid)
    m = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]], 
        zoom_start=16, 
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite Hybrid"
    )

    # Option Tile: Google Satellite Pure
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
        attr="Google Satellite Pure",
        name="Satelit Murni",
        overlay=False
    ).add_to(m)

    # Option Tile: OpenStreetMap
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Peta Jalan (OSM)",
        overlay=False
    ).add_to(m)

    # Layer Batas Wilayah
    if gdf_batas is not None:
        folium.GeoJson(gdf_batas, name="Batas Wilayah", style_function=lambda x: {'color': 'blue', 'fillOpacity': 0.1}).add_to(m)

    # Layer Toko Eksisting (Seluruh KML)
    if gdf_eksisting_raw is not None:
        folium.GeoJson(
            gdf_eksisting_raw,
            name="Toko Eksisting",
            marker=folium.Marker(icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa")),
            tooltip=folium.GeoJsonTooltip(
                fields=["Nama_Toko", "SPD_Display"],
                aliases=["Nama Toko:", "SPD Juni:"],
                localize=True,
                sticky=True
            )
        ).add_to(m)

    # Layer Kompetitor (Seluruh KML)
    if gdf_kompetitor_raw is not None:
        folium.GeoJson(
            gdf_kompetitor_raw,
            name="Kompetitor",
            marker=folium.Marker(icon=folium.Icon(color="orange", icon="store", prefix="fa")),
            tooltip=folium.GeoJsonTooltip(
                fields=["Nama_Toko", "Detail_Info"],
                aliases=["Nama Kompetitor:", "Detail:"],
                localize=True,
                sticky=True
            )
        ).add_to(m)

    # Titik Evaluasi & Radius Buffer
    folium.Marker(
        [st.session_state["selected_lat"], st.session_state["selected_lng"]],
        icon=folium.Icon(color="red", icon="info-sign"),
        tooltip="Titik Evaluasi Terpilih"
    ).add_to(m)

    folium.Circle(
        radius=radius_buffer,
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        color="blue",
        fill=True,
        fill_opacity=0.15
    ).add_to(m)

    # Layer Control
    folium.LayerControl(position="topright").add_to(m)

    # Event Handler Click Peta
    map_data = st_folium(m, width="100%", height=500)
    
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lng = map_data["last_clicked"]["lng"]
        if clicked_lat != st.session_state["selected_lat"] or clicked_lng != st.session_state["selected_lng"]:
            st.session_state["selected_lat"] = clicked_lat
            st.session_state["selected_lng"] = clicked_lng
            st.rerun()

with col_info:
    st.subheader("Hasil Analisis Potensi")
    st.markdown(f"""
    <div style="background-color: #064e3b; padding: 20px; border-radius: 8px; border-left: 4px solid #10b981; color: white;">
        <h4 style="margin: 0; color: #10b981;">DIREKOMENDASIKAN</h4>
        <p style="margin-top: 10px; font-size: 14px;">Lokasi ini direkomendasikan untuk analisis lebih lanjut dan survei lapangan.</p>
        <hr style="border-color: #047857;">
        <p style="margin: 0; font-size: 13px;"><b>Score Potensi:</b> {skor_total} / 100</p>
        <p style="margin: 0; font-size: 13px;"><b>Status:</b> Lanjutkan Survei</p>
    </div>
    """, unsafe_allow_html=True)
