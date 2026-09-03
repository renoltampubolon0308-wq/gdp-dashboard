st.set_page_config(
    page_title="Analisis Titik Potensi",
    page_icon="📍",
    layout="wide"
)

st.title("Analisis Titik Potensi")

# 1. SIDEBAR (PANEL KIRI)
st.sidebar.header("1. Unggah Data")
up_toko = st.sidebar.file_uploader("Titik Toko Eksisting (KML/KMZ)", type=["kml", "kmz"], key="up_toko")
up_kompetitor = st.sidebar.file_uploader("Titik Kompetitor (opsional, KML/KMZ)", type=["kml", "kmz"], key="up_komp")

st.sidebar.header("2. Kolom Target (Omzet)")

# 2. TAB UTAMA (TANPA EMOJI AGAR TIDAK ANOMALI/ERROR ENCODING)
tab1, tab2, tab3 = st.tabs(["Peta Toko", "Analisis Wilayah Baru", "Hasil"])
