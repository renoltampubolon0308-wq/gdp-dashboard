import streamlit as st
import folium
from streamlit_folium import st_folium

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="GDP Dashboard - Analisis Lokasi",
    page_icon="📍",
    layout="wide"
)

# --- 2. INISIALISASI SESSION STATE ---
# Menyimpan koordinat default (contoh: Jakarta/Lampung) jika belum ada
if "selected_lat" not in st.session_state:
    st.session_state["selected_lat"] = -5.39714  # Default Latitude
if "selected_lng" not in st.session_state:
    st.session_state["selected_lng"] = 105.26679 # Default Longitude

# --- 3. SIDEBAR: PARAMETER ANALISIS ---
with st.sidebar:
    st.header("PARAMETER ANALISIS")
    
    radius = st.number_input(
        "Radius Analisis (meter)",
        min_value=100,
        max_value=5000,
        value=1000,
        step=100
    )
    
    metode = st.selectbox(
        "Metode Penilaian",
        ["Weighted Overlay", "Buffer Analysis", "Multi-Criteria Decision"]
    )
    
    # Menampilkan koordinat aktif saat ini
    st.markdown("---")
    st.caption("📍 **Koordinat Evaluasi Saat Ini:**")
    st.code(f"Lat: {st.session_state['selected_lat']:.6f}\nLng: {st.session_state['selected_lng']:.6f}", language="text")
    
    # Tombol Jalankan Analisis
    btn_analisis = st.button("▶ JALANKAN ANALISIS", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.info("ℹ️ **Keterangan:**\nAnalisis menggunakan kepadatan bangunan Google Open Buildings serta data internal toko eksisting dan kompetitor.")

# --- 4. TAMPILAN UTAMA (PETA & HASIL EVALUASI) ---
col_map, col_result = st.columns([1.6, 1.2])

with col_map:
    st.caption("💡 *Klik pada peta di lokasi mana saja untuk memindahkan titik evaluasi.*")
    
    # Inisialisasi Peta Folium dengan CartoDB Dark Matter (sesuai tema dashboard Anda)
    m = folium.Map(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        zoom_start=15,
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
    )

    # Tambahkan Marker Titik Evaluasi yang Baru Diklik
    folium.Marker(
        location=[st.session_state["selected_lat"], st.session_state["selected_lng"]],
        popup="Titik Evaluasi",
        tooltip="Titik Evaluasi Terpilih",
        icon=folium.Icon(color="info", icon="info-sign", prefix="fa")
    ).add_to(m)

    # Render peta dan tangkap event klik dengan st_folium
    map_output = st_folium(
        m,
        width="100%",
        height=520,
        key="eval_map"
    )

    # Logika Pembaruan Titik saat Peta Diklik Pengguna
    if map_output and map_output.get("last_clicked"):
        clicked_lat = map_output["last_clicked"]["lat"]
        clicked_lng = map_output["last_clicked"]["lng"]
        
        # Cek apakah koordinat berbeda dengan state saat ini
        if (clicked_lat != st.session_state["selected_lat"]) or (clicked_lng != st.session_state["selected_lng"]):
            st.session_state["selected_lat"] = clicked_lat
            st.session_state["selected_lng"] = clicked_lng
            st.rerun()

with col_result:
    if btn_analisis:
        # Kotak Potensi Tinggi
        st.success("⭐ **POTENSI TINGGI**\n\nLokasi ini memiliki potensi yang baik untuk pengembangan toko baru.")
        
        # Skor Utama
        st.markdown("## Skor Potensi: **83 / 100**")
        st.progress(83)
        
        st.markdown("### Faktor Penilaian:")
        
        # Contoh Tabel Faktor Penilaian
        f1, f2 = st.columns([2, 1])
        f1.write("🏢 Kepadatan Bangunan")
        f2.write("**100 / 100**")
        
        f1, f2 = st.columns([2, 1])
        f1.write("🛣️ Akses Jalan")
        f2.write("**82 / 100**")
        
        f1, f2 = st.columns([2, 1])
        f1.write("🛒 Toko Eksisting (SPD)")
        f2.write("**70 / 100**")
        
        f1, f2 = st.columns([2, 1])
        f1.write("⚔️ Kompetitor")
        f2.write("**70 / 100**")
        
        f1, f2 = st.columns([2, 1])
        f1.write("📍 POI & Fasilitas")
        f2.write("**75 / 100**")
        
    else:
        st.info("👈 **Petunjuk:** Klik titik mana saja di peta untuk menempatkan marker, lalu klik tombol **▶ JALANKAN ANALISIS** di sidebar untuk menghitung potensi lokasi.")
