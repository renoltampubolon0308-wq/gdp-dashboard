import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Dashboard Analisis Lokasi")

# --- INITIAL STATE ---
# Coordinate awal (misal pusat kota/default)
if "selected_lat" not in st_session_state:
    st.session_state["selected_lat"] = -6.200000  # Default Latitude
if "selected_lng" not in st_session_state:
    st.session_state["selected_lng"] = 106.816666 # Default Longitude

st.title("📍 Dashboard Analisis Potensi Lokasi Toko")

# Layout Kolom (Sidebar Parameter & Peta, Hasil)
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Pilih Titik Lokasi Evaluasi")
    st.caption("💡 *Klik di mana saja pada peta untuk menempatkan Marker / Kursor Evaluasi.*")

    # 1. Buat Peta Folium
    m = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        zoom_start=15,
        tiles="OpenStreetMap" # atau tile CARTO/Mapbox pilihan Anda
    )

    # 2. Tambahkan Marker interaktif di posisi yang dipilih saat ini
    folium.Marker(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        popup=f"Titik Evaluasi<br>Lat: {st.session_state['selected_lat']:.5f}<br>Lng: {st.session_state['selected_lng']:.5f}",
        tooltip="Titik Evaluasi",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    # 3. Tangkap Event Klik menggunakan st_folium
    map_data = st_folium(
        m,
        width="100%",
        height=500,
        key="main_map"
    )

    # Update koordinat jika peta diklik oleh pengguna
    if map_data and map_data.get("last_clicked"):
        clicked_lat = map_data["last_clicked"]["lat"]
        clicked_lng = map_data["last_clicked"]["lng"]

        # Jika titik klik berbeda dari sebelumnya, simpan dan rerun
        if (clicked_lat != st.session_state["selected_lat"]) or (clicked_lng != st.session_state["selected_lng"]):
            st.session_state["selected_lat"] = clicked_lat
            st.session_state["selected_lng"] = clicked_lng
            st.rerun()

# --- SIDEBAR / PANEL PARAMETER ---
with st.sidebar:
    st.header("PARAMETER ANALISIS")
    
    # Menampilkan koordinat yang terpilih saat ini
    st.info(f"**Koordinat Terpilih:**\n- Lat: `{st.session_state['selected_lat']:.6f}`\n- Lng: `{st.session_state['selected_lng']:.6f}`")

    radius = st.number_input("Radius Analisis (meter)", min_value=100, max_value=5000, value=1000, step=100)
    metode = st.selectbox("Metode Penilaian", ["Weighted Overlay", "Buffer Analysis", "Multi-Criteria Decision"])

    # Tombol Jalankan Analisis
    btn_analisis = st.button("▶ JALANKAN ANALISIS", type="primary", use_container_width=True)

# --- KOPIKAN HASIL ANALISIS ---
with col_right:
    st.subheader("Hasil Analisis")
    
    if btn_analisis:
        st.success(f"Analisis berhasil dijalankan untuk titik (`{st.session_state['selected_lat']:.4f}`, `{st.session_state['selected_lng']:.4f}`)!")
        
        # --- CONTOH FUNGSI HITUNG ANALISIS PER TITIK ---
        # Di sini Anda panggil fungsi backend perhitungan (Spatial overlay/buffers/scoring)
        # berdasarkan st.session_state["selected_lat"] & st.session_state["selected_lng"]
        
        st.metric(label="Skor Potensi", value="83 / 100", delta="Potensi Tinggi")
        st.progress(83)

        st.markdown("### Faktor Penilaian:")
        st.write("🏢 **Kepadatan Bangunan:** 100 / 100")
        st.write("🛣️ **Akses Jalan:** 82 / 100")
        st.write("🛒 **Toko Eksisting:** 70 / 100")
        st.write("⚔️ **Kompetitor:** 70 / 100")
        st.write("📍 **POI & Fasilitas:** 75 / 100")
    else:
        st.info("Silakan klik lokasi pada peta di sebelah kiri, lalu klik **JALANKAN ANALISIS** pada menu di sebelah kiri.")
