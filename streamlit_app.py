import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd

# Import dari utils.py
from utils import (
    baca_kml, 
    hitung_kepadatan_google_buildings, 
    hitung_poin_radius, 
    kalkulasi_skor_potensi
)

st.set_page_config(
    page_title="Peta Persebaran Spasial",
    layout="wide"
)

# --- SIDEBAR (SETTINGS) ---
st.sidebar.header("Pengaturan Analisis")

file_bangunan = st.sidebar.file_uploader("Upload File Bangunan (KML / GeoJSON)", type=["kml", "geojson", "json"])
file_eksisting = st.sidebar.file_uploader("Upload File Toko Eksisting", type=["kml", "geojson"])
file_kompetitor = st.sidebar.file_uploader("Upload File Kompetitor", type=["kml", "geojson"])

radius_buffer = st.sidebar.slider("Pilih Radius Evaluasi (Meter)", min_value=100, max_value=1000, value=400, step=50)

# --- LOAD DATA ---
gdf_bangunan = baca_kml(file_bangunan) if file_bangunan else None
gdf_eksisting = baca_kml(file_eksisting) if file_eksisting else None
gdf_kompetitor = baca_kml(file_kompetitor) if file_kompetitor else None

# Default Koordinat
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -5.3850
if "selected_lng" not in st.session_state:
    st.session_state["selected_lng"] = 105.2900

cur_lat = st.session_state["selected_lat"]
cur_lng = st.session_state["selected_lng"]

# --- PERHITUNGAN DINAMIS ---
total_bangunan = hitung_kepadatan_google_buildings(gdf_bangunan, cur_lat, cur_lng, radius_buffer)
n_eksisting = hitung_poin_radius(gdf_eksisting, cur_lat, cur_lng, radius_buffer)
n_kompetitor = hitung_poin_radius(gdf_kompetitor, cur_lat, cur_lng, radius_buffer)
skor_total, _ = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)

# --- 1. SECTION PETA (SINGLE MAP) ---
st.subheader("Peta Persebaran Spasial")
st.caption("Klik lokasi mana saja pada peta untuk memindahkan titik evaluasi.")

# Peta Satelit Google Hybrid (SATU PETA SAJA)
m = folium.Map(
    location=[cur_lat, cur_lng],
    zoom_start=16,
    tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attr="Google Satellite Hybrid"
)

# Marker Titik Evaluasi & Buffer
folium.Marker(
    [cur_lat, cur_lng],
    popup="Titik Evaluasi",
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(m)

folium.Circle(
    [cur_lat, cur_lng],
    radius=radius_buffer,
    color="blue",
    fill=True,
    fill_color="blue",
    fill_opacity=0.15
).add_to(m)

# Tampilkan Layer Bangunan jika ada
if gdf_bangunan is not None:
    folium.GeoJson(
        gdf_bangunan,
        style_function=lambda x: {"fillColor": "#ffcc00", "color": "#ffaa00", "weight": 1, "fillOpacity": 0.4}
    ).add_to(m)

# HANYA SATU KALI CALL st_folium DENGAN key UNIK
map_data = st_folium(m, width="100%", height=480, key="main_map")

if map_data and map_data.get("last_clicked"):
    new_lat = map_data["last_clicked"]["lat"]
    new_lng = map_data["last_clicked"]["lng"]
    if abs(new_lat - cur_lat) > 0.00001 or abs(new_lng - cur_lng) > 0.00001:
        st.session_state["selected_lat"] = new_lat
        st.session_state["selected_lng"] = new_lng
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# --- 2. SECTION INSIGHT LOKASI & REKOMENDASI ---
col_insight, col_rekomendasi = st.columns([3, 1.4])

with col_insight:
    st.markdown("### 💡 Insight Lokasi")
    ins_1, ins_2, ins_3, ins_4 = st.columns(4)
    
    # Kepadatan Bangunan
    txt_bangunan = "TINGGI" if total_bangunan >= 800 else ("SEDANG" if total_bangunan >= 300 else "RENDAH")
    with ins_1:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; min-height: 150px;">
            <div style="color: #22c55e; font-size: 13px; font-weight: bold;">Kepadatan Bangunan</div>
            <div style="color: #22c55e; font-size: 20px; font-weight: bold; margin: 8px 0;">{txt_bangunan}</div>
            <div style="color: #94a3b8; font-size: 12px;">{total_bangunan:,} bangunan dalam radius {radius_buffer/1000:.1f} km.</div>
        </div>
        """, unsafe_allow_html=True)
        
    # Akses Jalan
    with ins_2:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; min-height: 150px;">
            <div style="color: #22c55e; font-size: 13px; font-weight: bold;">Akses Jalan</div>
            <div style="color: #22c55e; font-size: 20px; font-weight: bold; margin: 8px 0;">TINGGI</div>
            <div style="color: #94a3b8; font-size: 12px;">Dekat dengan jaringan jalan utama.</div>
        </div>
        """, unsafe_allow_html=True)

    # Kompetitor
    txt_komp = "TINGGI" if n_kompetitor > 5 else ("SEDANG" if n_kompetitor > 0 else "TIDAK ADA")
    color_komp = "#eab308" if n_kompetitor > 0 else "#22c55e"
    with ins_3:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; min-height: 150px;">
            <div style="color: #eab308; font-size: 13px; font-weight: bold;">Kompetitor</div>
            <div style="color: {color_komp}; font-size: 20px; font-weight: bold; margin: 8px 0;">{txt_komp}</div>
            <div style="color: #94a3b8; font-size: 12px;">{n_kompetitor} toko terdeteksi.</div>
        </div>
        """, unsafe_allow_html=True)

    # Toko Eksisting
    txt_eks = "ADA" if n_eksisting > 0 else "TIDAK ADA"
    with ins_4:
        st.markdown(f"""
        <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border: 1px solid #334155; min-height: 150px;">
            <div style="color: #22c55e; font-size: 13px; font-weight: bold;">Toko Eksisting</div>
            <div style="color: #22c55e; font-size: 20px; font-weight: bold; margin: 8px 0;">{txt_eks}</div>
            <div style="color: #94a3b8; font-size: 12px;">Terdapat {n_eksisting} toko eksisting di area ini.</div>
        </div>
        """, unsafe_allow_html=True)

with col_rekomendasi:
    st.markdown("### 🎯 Rekomendasi")
    
    is_recom = skor_total >= 70
    bg_box = "#064e3b" if is_recom else "#7f1d1d"
    border_box = "#10b981" if is_recom else "#ef4444"
    status_title = "DIREKOMENDASIKAN" if is_recom else "TIDAK DIREKOMENDASIKAN"
    status_sub = "Lanjutkan Survei" if is_recom else "Cari Lokasi Lain"
    desc_txt = "Lokasi ini direkomendasikan untuk analisis lebih lanjut dan survei lapangan." if is_recom else "Skor potensi di bawah ambang batas standar."

    st.markdown(f"""
    <div style="background-color: {bg_box}; padding: 18px; border-radius: 8px; border: 1px solid {border_box}; color: white; min-height: 150px;">
        <h4 style="margin: 0; color: {border_box}; font-size: 16px;">{status_title}</h4>
        <p style="margin-top: 8px; font-size: 12px; color: #e2e8f0;">{desc_txt}</p>
        <hr style="border-color: {border_box}; margin: 10px 0;">
        <p style="margin: 0; font-size: 12px;"><b>Score Potensi:</b> {skor_total} / 100</p>
        <p style="margin: 0; font-size: 12px;"><b>Status:</b> {status_sub}</p>
    </div>
    """, unsafe_allow_html=True)
