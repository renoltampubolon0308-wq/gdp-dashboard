import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd

# Import fungsi pembantu dari utils.py
from utils import (
    baca_kml, 
    hitung_kepadatan_google_buildings, 
    hitung_poin_radius, 
    kalkulasi_skor_potensi
)

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Peta Persebaran Spasial & Analisis Potensi",
    layout="wide"
)

st.title("Peta Persebaran Spasial")

# --- SIDEBAR PANEL (SETTINGS & FILE UPLOADER) ---
st.sidebar.header("Pengaturan Analisis")

# Upload File Spatial Bangunan (Google Open Buildings KML/GeoJSON)
file_bangunan = st.sidebar.file_uploader(
    "Upload File Bangunan (KML / GeoJSON)", 
    type=["kml", "geojson", "json"]
)

# Upload File Point Eksisting & Kompetitor (Opsional)
file_eksisting = st.sidebar.file_uploader("Upload File Toko Eksisting", type=["kml", "geojson"])
file_kompetitor = st.sidebar.file_uploader("Upload File Kompetitor", type=["kml", "geojson"])

# Radius Buffer
radius_buffer = st.sidebar.slider(
    "Pilih Radius Evaluasi (Meter)", 
    min_value=100, 
    max_value=1000, 
    value=400, 
    step=50
)

# --- LOAD DATA SPASIAL ---
gdf_bangunan = baca_kml(file_bangunan) if file_bangunan else None
gdf_eksisting = baca_kml(file_eksisting) if file_eksisting else None
gdf_kompetitor = baca_kml(file_kompetitor) if file_kompetitor else None

# Default Koordinat Pusat (Harapan Raya / Sukarame, Bandar Lampung)
DEFAULT_LAT = -5.3850
DEFAULT_LNG = 105.2900

# Inisialisasi State Koordinat yang Diklik
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = DEFAULT_LAT
if "selected_lng" not in st.session_state:
    st.session_state["selected_lng"] = DEFAULT_LNG

# --- BACA EVENT KLIK DARI PETA ---
st.caption("Click lokasi mana saja pada peta untuk memindahkan titik evaluasi.")

col_peta, col_hasil = st.columns([1.6, 1])

with col_peta:
    # Buat Peta Folium
    m = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        zoom_start=15,
        tiles="OpenStreetMap"
    )

    # Tambahkan Marker Titik Evaluasi yang Sedang Dipilih
    folium.Marker(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        popup="Titik Evaluasi",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(m)

    # Tambahkan Lingkaran Buffer di Peta
    folium.Circle(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        radius=radius_buffer,
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.15
    ).add_to(m)

    # Menampilkan Overlay GeoDataFrame Bangunan jika diupload
    if gdf_bangunan is not None:
        folium.GeoJson(
            gdf_bangunan,
            name="Google Buildings",
            style_function=lambda x: {
                "fillColor": "#888888",
                "color": "#444444",
                "weight": 0.5,
                "fillOpacity": 0.3
            }
        ).add_to(m)

    # Render Peta dan Tangkap Event Click
    map_data = st_folium(m, width="100%", height=500)

    # Update koordinat session state jika ada klik baru di peta
    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lng = map_data["last_clicked"]["lng"]
        
        # Perbarui state & rerun jika titik bergeser
        if new_lat != st.session_state["selected_lat"] or new_lng != st.session_state["selected_lng"]:
            st.session_state["selected_lat"] = new_lat
            st.session_state["selected_lng"] = new_lng
            st.rerun()

# --- PROSES HITUNG ANALISIS DINAMIS ---
cur_lat = st.session_state["selected_lat"]
cur_lng = st.session_state["selected_lng"]

# Hitung jumlah bangunan dinamis dari titik klik
total_bangunan = hitung_kepadatan_google_buildings(
    gdf_bangunan, 
    cur_lat, 
    cur_lng, 
    radius_buffer
)

# Hitung eksisting & kompetitor dalam radius
n_eksisting = hitung_poin_radius(gdf_eksisting, cur_lat, cur_lng, radius_buffer)
n_kompetitor = hitung_poin_radius(gdf_kompetitor, cur_lat, cur_lng, radius_buffer)

# Kalkulasi Skor Potensi Dinamis
skor_total, rincian = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)

# --- PANEL HASIL ANALISIS POTENSI ---
with col_hasil:
    st.subheader("Hasil Analisis Potensi")
    
    # Logika Penentuan Rekomendasi
    is_recom = skor_total >= 70
    status_text = "DIREKOMENDASIKAN" if is_recom else "TIDAK DIREKOMENDASIKAN"
    status_bg = "#0d5c3a" if is_recom else "#701616"
    status_desc = (
        "Lokasi ini direkomendasikan untuk analisis lebih lanjut dan survei lapangan." 
        if is_recom else 
        "Lokasi ini tidak direkomendasikan karena potensi kepadatan rendah atau kompetisi tinggi."
    )
    
    # Card Hasil Rekomendasi
    st.markdown(
        f"""
        <div style="background-color: {status_bg}; padding: 20px; border-radius: 10px; color: white;">
            <h2 style="margin: 0; color: #43f3a2;">{status_text}</h2>
            <p style="margin-top: 10px; font-size: 14px;">{status_desc}</p>
            <hr style="border: 0.5px solid #ffffff55;">
            <h4 style="margin: 5px 0;">Score Potensi: {skor_total} / 100</h4>
            <p style="margin: 0; font-size: 13px;">Status: {"Lanjutkan Survei" if is_recom else "Batal / Cari Lokasi Lain"}</p>
        </div>
        """,
        unsafe_clause=True,
        unsafe_allow_html=True
    )
    
    # Detail Indikator Spasial
    st.write("---")
    st.markdown("##### **Detail Indikator Spasial:**")
    st.write(f"- **Jumlah Bangunan (Radius {radius_buffer}m):** `{total_bangunan}` bangunan")
    st.write(f"- **Toko Eksisting Dalam Radius:** `{n_eksisting}` toko")
    st.write(f"- **Kompetitor Dalam Radius:** `{n_kompetitor}` toko")
    
    with st.expander("Rincian Poin Penilaian"):
        st.json(rincian)
