import streamlit as st
import folium
from streamlit_folium import st_folium
import geopandas as gpd

# Import fungsi dari utils.py
from utils import (
    baca_kml, 
    hitung_kepadatan_google_buildings, 
    hitung_poin_radius, 
    kalkulasi_skor_potensi
)

st.set_page_config(
    page_title="Analisis Lokasi Berbasis Google Open Buildings",
    layout="wide"
)

# Custom CSS untuk menyelaraskan tampilan UI dengan gambar
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e2530;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #2d3748;
        min-height: 120px;
    }
    .metric-title {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 800;
        color: #ffffff;
    }
    .metric-sub {
        font-size: 11px;
        color: #94a3b8;
        margin-top: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR PENGATURAN ---
st.sidebar.header("Pengaturan Analisis")
file_bangunan = st.sidebar.file_uploader("Upload File Bangunan (KML / GeoJSON)", type=["kml", "geojson", "json"])
file_eksisting = st.sidebar.file_uploader("Upload File Toko Eksisting", type=["kml", "geojson"])
file_kompetitor = st.sidebar.file_uploader("Upload File Kompetitor", type=["kml", "geojson"])
radius_buffer = st.sidebar.slider("Pilih Radius Evaluasi (Meter)", min_value=100, max_value=1000, value=400, step=50)

# Load Data
gdf_bangunan = baca_kml(file_bangunan) if file_bangunan else None
gdf_eksisting = baca_kml(file_eksisting) if file_eksisting else None
gdf_kompetitor = baca_kml(file_kompetitor) if file_kompetitor else None

# State Koordinat Klik
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -5.3850
if "selected_lng" not in st.session_state:
    st.session_state["selected_lng"] = 105.2900

cur_lat = st.session_state["selected_lat"]
cur_lng = st.session_state["selected_lng"]

# --- HITUNG DATA DINAMIS BERDASARKAN TITIK KLIK ---
total_bangunan = hitung_kepadatan_google_buildings(gdf_bangunan, cur_lat, cur_lng, radius_buffer)
n_eksisting = hitung_poin_radius(gdf_eksisting, cur_lat, cur_lng, radius_buffer)
n_kompetitor = hitung_poin_radius(gdf_kompetitor, cur_lat, cur_lng, radius_buffer)
skor_total, _ = kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor)

# Header Utama
st.caption("Analisis Lokasi Berbasis Google Open Buildings + Data Internal")

# --- 1. BARIS METRIK KARTU ATAS (5 KARTU) ---
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    txt_status = "Sangat Potensial 🎯" if skor_total >= 75 else ("Potensial" if skor_total >= 50 else "Kurang Potensial")
    st.markdown(f"""
    <div class="metric-card" style="border-left: 3px solid #22c55e;">
        <div class="metric-title" style="color: #22c55e;">SKOR POTENSI</div>
        <div class="metric-value">{skor_total} <span style="font-size:16px; font-weight:normal; color:#94a3b8;">/ 100</span></div>
        <div class="metric-sub" style="color: #22c55e; font-weight: 600;">{txt_status}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #3b82f6;">BANGUNAN (GOOGLE)</div>
        <div class="metric-value">{total_bangunan:,}</div>
        <div class="metric-sub">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #a855f7;">TOKO EKSISTING</div>
        <div class="metric-value">{n_eksisting}</div>
        <div class="metric-sub">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title" style="color: #f97316;">KOMPETITOR</div>
        <div class="metric-value">{n_kompetitor}</div>
        <div class="metric-sub">dalam radius {radius_buffer/1000:.1f} km</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown("""
    <div class="metric-card">
        <div class="metric-title" style="color: #e2e8f0;">SPD TOKO EKSISTING</div>
        <div class="metric-value">Rp 12,5 jt</div>
        <div class="metric-sub">rata-rata / hari</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 2. BARIS UTAMA (PETA & HASIL ANALISIS) ---
col_peta, col_hasil = st.columns([1.8, 1])

with col_peta:
    st.subheader("Peta Persebaran Spasial")
    st.caption("💡 *Klik lokasi mana saja pada peta untuk memindahkan titik evaluasi.*")
    
    # Filter Checkbox Layer Peta
    cb1, cb2, cb3, cb4 = st.columns(4)
    show_bng = cb1.checkbox("Bangunan", value=True)
    show_eks = cb2.checkbox("Toko Eksisting", value=True)
    show_komp = cb3.checkbox("Kompetitor", value=True)
    show_bts = cb4.checkbox("Batas Wilayah", value=True)

    # Inisialisasi Peta Folium (Tampilan Jalan OpenStreetMap seperti di screenshot kamu)
    m = folium.Map(location=[cur_lat, cur_lng], zoom_start=15, tiles="OpenStreetMap")

    # Marker Evaluasi & Buffer
    folium.Marker([cur_lat, cur_lng], popup="Titik Evaluasi", icon=folium.Icon(color="red", icon="info-sign")).add_to(m)
    folium.Circle([cur_lat, cur_lng], radius=radius_buffer, color="blue", fill=True, fill_color="blue", fill_opacity=0.15).add_to(m)

    # Layer Tampilan Berdasarkan Checkbox
    if show_bng and gdf_bangunan is not None:
        folium.GeoJson(gdf_bangunan, style_function=lambda x: {"fillColor": "#3b82f6", "color": "#1d4ed8", "weight": 0.5}).add_to(m)

    # Render Peta
    map_data = st_folium(m, width="100%", height=420, key="map_eval")

    if map_data and map_data.get("last_clicked"):
        new_lat = map_data["last_clicked"]["lat"]
        new_lng = map_data["last_clicked"]["lng"]
        if abs(new_lat - cur_lat) > 0.00001 or abs(new_lng - cur_lng) > 0.00001:
            st.session_state["selected_lat"] = new_lat
            st.session_state["selected_lng"] = new_lng
            st.rerun()

with col_hasil:
    st.subheader("Hasil Analisis Potensi")
    
    is_potensial = skor_total >= 70
    box_bg = "#064e3b" if is_potensial else "#7f1d1d"
    box_border = "#10b981" if is_potensial else "#ef4444"
    title_text = "⭐ POTENSI TINGGI" if is_potensial else "⚠️ POTENSI RENDAH"
    desc_text = "Lokasi ini memiliki potensi yang baik untuk pengembangan toko baru." if is_potensial else "Lokasi kurang disarankan karena kepadatan bangunan rendah atau persaingan tinggi."

    st.markdown(f"""
    <div style="background-color: {box_bg}; border: 1px solid {box_border}; padding: 20px; border-radius: 8px; color: white;">
        <h4 style="margin: 0; color: #34d399; font-size: 16px;">{title_text}</h4>
        <p style="margin-top: 10px; font-size: 13px; color: #e2e8f0; line-height: 1.4;">{desc_text}</p>
    </div>
    """, unsafe_allow_html=True)
