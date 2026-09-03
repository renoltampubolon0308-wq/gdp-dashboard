import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from utils import baca_kml, hitung_kepadatan_google_buildings

st.set_page_config(
    page_title="Dashboard Analisis Potensi Lokasi Toko",
    page_icon="🏪",
    layout="wide"
)

st.title("🏪 Dashboard Penilaian Potensi Lokasi (Google Buildings Focused)")
st.write("Analisis gabungan KML internal dan dataset Google Open Buildings Parquet.")

# ---------------------------------------------------------
# SIDEBAR - INPUT DATA KML
# ---------------------------------------------------------
st.sidebar.header("1. Upload Layer KML Internal")
file_batas = st.sidebar.file_uploader("Upload Batas Wilayah (KML/KMZ)", type=["kml", "kmz"])
file_toko_eksisting = st.sidebar.file_uploader("Upload Toko Eksisting & SPD (KML/KMZ)", type=["kml", "kmz"])
file_kompetitor = st.sidebar.file_uploader("Upload Toko Kompetitor & SPD (KML/KMZ)", type=["kml", "kmz"])

st.sidebar.markdown("---")
st.sidebar.header("2. Parameter Buffer")
radius_buffer = st.sidebar.slider("Radius Analisis Buffer (Meter)", 200, 3000, 1000, step=100)

# BACA FILE KML
gdf_batas = baca_kml(file_batas) if file_batas else None
gdf_eksisting = baca_kml(file_toko_eksisting) if file_toko_eksisting else None
gdf_kompetitor = baca_kml(file_kompetitor) if file_kompetitor else None

col1, col2 = st.columns([2, 1])

# Menentukan Koordinat Pusat Peta
center_lat, center_lon = -6.200000, 106.816666

if gdf_batas is not None and not gdf_batas.empty:
    bounds = gdf_batas.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
elif gdf_eksisting is not None and not gdf_eksisting.empty:
    bounds = gdf_eksisting.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

# ---------------------------------------------------------
# RENDERING PETA (FOLIUM)
# ---------------------------------------------------------
with col1:
    st.subheader("🗺️ Peta Persebaran Spasial")
    m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # 1. Batas Wilayah
    if gdf_batas is not None:
        folium.GeoJson(
            gdf_batas,
            name="Batas Wilayah",
            style_function=lambda x: {'fillColor': '#3186cc', 'color': '#1a5276', 'weight': 2, 'fillOpacity': 0.2}
        ).add_to(m)

    # 2. Toko Eksisting & SPD (Marker Hijau)
    if gdf_eksisting is not None:
        for idx, row in gdf_eksisting.iterrows():
            geom = row.geometry
            if geom.geom_type == 'Point':
                nama = row.get('Name', f"Toko Eksisting #{idx+1}")
                spd_val = row.get('SPD', row.get('spd', 'N/A'))
                folium.Marker(
                    location=[geom.y, geom.x],
                    popup=f"<b>{nama}</b><br>SPD: {spd_val}",
                    tooltip=nama,
                    icon=folium.Icon(color="green", icon="shopping-cart", prefix="fa")
                ).add_to(m)

    # 3. Kompetitor & SPD (Marker Merah)
    if gdf_kompetitor is not None:
        for idx, row in gdf_kompetitor.iterrows():
            geom = row.geometry
            if geom.geom_type == 'Point':
                nama = row.get('Name', f"Kompetitor #{idx+1}")
                spd_val = row.get('SPD', row.get('spd', 'N/A'))
                folium.Marker(
                    location=[geom.y, geom.x],
                    popup=f"<b>{nama}</b><br>SPD: {spd_val}",
                    tooltip=nama,
                    icon=folium.Icon(color="red", icon="store", prefix="fa")
                ).add_to(m)

    # Circle Buffer Area
    folium.Circle(
        location=[center_lat, center_lon],
        radius=radius_buffer,
        color="purple",
        fill=True,
        fill_opacity=0.15,
        popup=f"Area Radius {radius_buffer}m"
    ).add_to(m)

    st_folium(m, width="100%", height=550)

# ---------------------------------------------------------
# ANALISIS POTENSI MENGGUNAKAN DATASET GOOGLE BUILDINGS
# ---------------------------------------------------------
with col2:
    st.subheader("📊 Analisis Potensi (Google Dataset)")
    
    if st.button("🚀 Hitung Potensi Wilayah"):
        with st.spinner("Menganalisis dataset Google Open Buildings Parquet..."):
            total_bangunan, total_luas = hitung_kepadatan_google_buildings(
                center_lat, center_lon, radius_buffer
            )

            # Klasifikasi Potensi Berdasarkan Kepadatan Bangunan Google
            # Semakin banyak bangunan & makin luas, potensi pasar makin besar
            if total_bangunan >= 1000:
                skor_label = "SANGAT POTENSIAL 💥"
                keterangan = "Kepadatan bangunan dan pemukiman sangat tinggi."
                st.success(f"**Klasifikasi: {skor_label}**")
            elif total_bangunan >= 300:
                skor_label = "POTENSIAL SEDANG ⚠️"
                keterangan = "Kepadatan bangunan lumayan berkembang."
                st.warning(f"**Klasifikasi: {skor_label}**")
            else:
                skor_label = "KURANG POTENSIAL ❌"
                keterangan = "Jumlah bangunan di sekitar buffer tergolong renggang."
                st.error(f"**Klasifikasi: {skor_label}**")

            st.caption(keterangan)

            st.markdown("---")
            st.markdown("#### 🏢 Google Open Buildings Metrics")
            st.metric("Total Bangunan Terdeteksi", f"{total_bangunan:,} unit")
            st.metric("Total Luas Jejak Bangunan", f"{total_luas:,.0f} m²")
            
            if total_bangunan > 0:
                rata_luas = total_luas / total_bangunan
                st.metric("Rata-rata Luas Bangunan", f"{rata_luas:.1f} m²")

            # Data Kompetitor & Eksisting Internal
            st.markdown("---")
            st.markdown("#### 🏪 Data Ekosistem Internal")
            n_eksisting = len(gdf_eksisting) if gdf_eksisting is not None else 0
            n_kompetitor = len(gdf_kompetitor) if gdf_kompetitor is not None else 0
            
            st.write(f"• **Toko Eksisting:** {n_eksisting} titik")
            st.write(f"• **Toko Kompetitor:** {n_kompetitor} titik")

    else:
        st.info("Klik **🚀 Hitung Potensi Wilayah** untuk mengeksekusi perhitungan Parquet Google.")

# ---------------------------------------------------------
# TABEL DETAIL KML
# ---------------------------------------------------------
st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📋 Batas Wilayah", "🛒 Toko Eksisting & SPD", "⚔️ Toko Kompetitor & SPD"])

with tab1:
    if gdf_batas is not None:
        st.dataframe(gdf_batas.drop(columns=['geometry'], errors='ignore'))
    else:
        st.write("Belum ada file KML Batas Wilayah.")

with tab2:
    if gdf_eksisting is not None:
        st.dataframe(gdf_eksisting.drop(columns=['geometry'], errors='ignore'))
    else:
        st.write("Belum ada file KML Toko Eksisting.")

with tab3:
    if gdf_kompetitor is not None:
        st.dataframe(gdf_kompetitor.drop(columns=['geometry'], errors='ignore'))
    else:
        st.write("Belum ada file KML Toko Kompetitor.")
