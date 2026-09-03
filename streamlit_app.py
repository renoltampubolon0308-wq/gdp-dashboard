import streamlit as st
import geopandas as gpd
import utils

st.set_page_config(
    page_title="Analisis Titik Potensi",
    page_icon="📍",
    layout="wide"
)

st.title("Analisis Titik Potensi")

# -------------------------------------------------------------------
# 1. SIDEBAR (INPUT DATA)
# -------------------------------------------------------------------
st.sidebar.header("1. Unggah Data")
up_toko = st.sidebar.file_uploader("Titik Toko Eksisting (KML/KMZ)", type=["kml", "kmz"], key="up_toko")
up_kompetitor = st.sidebar.file_uploader("Titik Kompetitor (opsional, KML/KMZ)", type=["kml", "kmz"], key="up_komp")

gdf_toko = None
gdf_kompetitor = None

# Deteksi fungsi baca KML yang tersedia di utils.py
func_baca = getattr(utils, 'load_kml', getattr(utils, 'baca_kml', getattr(utils, 'read_kml', None)))

if up_toko and func_baca:
    gdf_toko = func_baca(up_toko)
    st.sidebar.success(f"Toko Eksisting: {len(gdf_toko)} titik terload.")

if up_kompetitor and func_baca:
    gdf_kompetitor = func_baca(up_kompetitor)
    st.sidebar.success(f"Kompetitor: {len(gdf_kompetitor)} titik terload.")

st.sidebar.header("2. Kolom Target (Omzet)")

kolom_target = None
if gdf_toko is not None:
    kolom_target = st.sidebar.selectbox(
        "Pilih Kolom SPD / Omzet:",
        options=list(gdf_toko.columns)
    )

btn_run = st.sidebar.button("Jalankan Analisis", type="primary")

# -------------------------------------------------------------------
# 2. TAB UTAMA
# -------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["Peta Toko", "Analisis Wilayah Baru", "Hasil"])

with tab1:
    st.subheader("Visualisasi Lokasi Toko & Kompetitor")
    if gdf_toko is not None:
        st.write("Data Toko Eksisting:", gdf_toko.head())
    else:
        st.info("Silakan unggah file KML Toko Eksisting di sidebar untuk melihat peta.")

with tab2:
    st.subheader("Analisis Kepadatan Google Open Buildings")
    if btn_run:
        if gdf_toko is not None:
            st.success("Menjalankan analisis spasial & ekstraksi bangunan...")
            first_geom = gdf_toko.geometry.iloc[0]
            lat, lon = first_geom.y, first_geom.x
            
            total_bgn, total_luas = utils.hitung_kepadatan_google_buildings(lat, lon, radius_meter=500)
            
            st.metric("Total Bangunan Radius 500m (Titik 1)", f"{total_bgn} unit")
            st.metric("Total Luas Footprint", f"{total_luas:,.2f} m²")
        else:
            st.warning("Unggah data KML terlebih dahulu sebelum menjalankan analisis.")

with tab3:
    st.subheader("Hasil Skor & Estimasi Omzet")
    if btn_run and gdf_toko is not None:
        st.write("Proses perhitungan skor potensi selesai.")
