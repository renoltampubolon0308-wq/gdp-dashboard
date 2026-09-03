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

# --- SIDEBAR (SETTINGS & FILE UPLOADER) ---
st.sidebar.header("Pengaturan Analisis")

file_bangunan = st.sidebar.file_uploader("Upload File Bangunan (KML / GeoJSON)", type=["kml", "geojson", "json"])
file_eksisting = st.sidebar.file_uploader("Upload File Toko Eksisting", type=["kml", "geojson"])
file_kompetitor = st.sidebar.file_uploader("Upload File Kompetitor", type=["kml", "geojson"])

radius_buffer = st.sidebar.slider("Pilih Radius Evaluasi (Meter)", min_value=100, max_value=1000, value=400, step=50)

# --- LOAD DATA SPASIAL ---
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

# --- PERHITUNGAN DINAMIS BERDASARKAN TITIK KLIK ---
total_bangunan = hitung_kepadatan_google_buildings(gdf_bangunan, cur_lat, cur_lng, radius_buffer)
n_eksisting = hitung_poin_radius(gdf_eksisting, cur_lat, cur_lng, radius_buffer)
n_kompetitor = hitung_poin_radius(gdf_kompetitor, cur_lat, cur_lng, radius_buffer)

skor_total, rincian = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)

# --- 1. BARIS 4 KARTU STATISTIK (ATAS) ---
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    txt_b = "Potensial" if total_bangunan >= 500 else "Rendah"
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid #334155;">
        <div style="color: #22c55e; font-size: 16px; font-weight: bold;">{txt_b}</div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">Kepadatan Bangunan</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid #334155;">
        <div style="color: #e2e8f0; font-size: 16px; font-weight: bold;">{total_bangunan:,}</div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid #334155;">
        <div style="color: #e2e8f0; font-size: 16px; font-weight: bold;">{n_eksisting} Toko</div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid #334155;">
        <div style="color: #e2e8f0; font-size: 16px; font-weight: bold;">{n_kompetitor} Kompetitor</div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 12px; border-radius: 6px; border: 1px solid #334155;">
        <div style="color: #e2e8f0; font-size: 16px; font-weight: bold;">{cur_lat:.4f}, {cur_lng:.4f}</div>
        <div style="color: #94a3b8; font-size: 11px; margin-top: 4px;">koordinat terpilih</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 2. BARIS UTAMA (PETA & REKOMENDASI BERDAMPINGAN) ---
col_left, col_right = st.columns([1.7, 1])

with col_left:
    st.subheader("Peta Persebaran Spasial")
    st.caption("Click lokasi mana saja pada peta untuk memindahkan titik evaluasi.")

    # Peta Google Satellite Hybrid
    m = folium.Map(
        location=[cur_lat, cur_lng],
        zoom_start=16,
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite Hybrid"
    )

    # Marker Evaluasi & Circle Buffer
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

    # Tampilkan Layer Bangunan jika diupload
    if gdf_bangunan is not None:
        folium.GeoJson(
            gdf_bangunan,
            style_function=lambda x: {"fillColor": "#ffcc00", "color": "#ffaa00", "weight": 1, "fillOpacity": 0.4}
        ).add_to(m)

    # Render Peta
    map_data = st_folium(m, width="100%", height=480, key="main_map")

    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lng = map_data["last_clicked"]["lng"]
        if abs(new_lat - cur_lat) > 0.00001 or abs(new_lng - cur_lng) > 0.00001:
            st.session_state["selected_lat"] = new_lat
            st.session_state["selected_lng"] = new_lng
            st.rerun()

with col_right:
    st.subheader("Hasil Analisis Potensi")
    
    is_recom = skor_total >= 70
    bg_color = "#0b4d34" if is_recom else "#611313"
    txt_status = "DIREKOMENDASIKAN" if is_recom else "TIDAK DIREKOMENDASIKAN"
    txt_desc = (
        "Lokasi ini direkomendasikan untuk analisis lebih lanjut dan survei lapangan."
        if is_recom else
        "Lokasi kurang berpotensi karena kepadatan bangunan rendah atau persaingan tinggi."
    )
    txt_action = "Lanjutkan Survei" if is_recom else "Batal / Cari Lokasi Lain"

    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 25px; border-radius: 12px; color: white; height: 480px; display: flex; flex-direction: column; justify-content: center;">
        <h2 style="color: #34d399; font-weight: bold; margin-bottom: 15px;">{txt_status}</h2>
        <p style="font-size: 15px; color: #e2e8f0; line-height: 1.5;">{txt_desc}</p>
        <hr style="border-color: #ffffff33; margin: 25px 0;">
        <h4 style="margin: 0 0 8px 0; font-size: 18px;">Score Potensi: {skor_total} / 100</h4>
        <p style="margin: 0; font-size: 14px; color: #cbd5e1;">Status: {txt_action}</p>
    </div>
    """, unsafe_allow_html=True)
