import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from utils import baca_kml, hitung_kepadatan_google_buildings

# Pengaturan Halaman
st.set_page_config(
    page_title="GDP Dashboard",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Spatial GDP & Building Density Dashboard")
st.write("Visualisasi data spasial dan estimasi kepadatan bangunan.")

# Sidebar untuk Input Data
st.sidebar.header("Upload Data Spasial")
uploaded_file = st.sidebar.file_uploader("Pilih file KML atau KMZ", type=["kml", "kmz"])

col1, col2 = st.columns([2, 1])

if uploaded_file is not None:
    # Membaca File KML/KMZ menggunakan utils.py
    with st.spinner("Membaca data KML/KMZ..."):
        gdf = baca_kml(uploaded_file)

    if gdf is not None and not gdf.empty:
        st.sidebar.success("File berhasil dimuat!")

        # Menampilkan Peta
        with col1:
            st.subheader("Peta Batas Wilayah / Point")
            
            # Hitung titik tengah peta
            bounds = gdf.total_bounds
            center_lat = (bounds[1] + bounds[3]) / 2
            center_lon = (bounds[0] + bounds[2]) / 2

            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)

            # Tambahkan GeoJSON ke peta
            folium.GeoJson(
                gdf,
                name="Data KML",
                style_function=lambda x: {
                    'fillColor': '#3186cc',
                    'color': '#3186cc',
                    'weight': 2,
                    'fillOpacity': 0.4,
                }
            ).add_to(m)

            st_folium(m, width="100%", height=500)

        # Informasi & Analisis Tambahan
        with col2:
            st.subheader("Detail Data Spasial")
            st.write(f"**Jumlah Objek:** {len(gdf)}")
            
            # Analisis Kepadatan Bangunan (Mengambil koordinat pusat)
            st.subheader("Analisis Google Open Buildings")
            radius = st.slider("Radius Analisis (Meter)", 100, 2000, 500, step=100)
            
            if st.button("Hitung Kepadatan Bangunan"):
                with st.spinner("Menghitung data Google Open Buildings..."):
                    total_bangunan, total_luas = hitung_kepadatan_google_buildings(
                        center_lat, center_lon, radius_meter=radius
                    )
                    st.metric("Total Bangunan Terdeteksi", f"{total_bangunan:,}")
                    st.metric("Total Luas Bangunan (m²)", f"{total_luas:,.2f}")

        # Tabel Data
        st.subheader("Tabel Atribut")
        st.dataframe(gdf.drop(columns=['geometry'], errors='ignore'))

    else:
        st.error("Gagal membaca file KML/KMZ. Pastikan format file benar.")
else:
    st.info("Silakan upload file KML atau KMZ melalui sidebar di sebelah kiri untuk mulai mengamati data.")
