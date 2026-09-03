import geopandas as gpd
import fiona
from shapely.geometry import Point
from bs4 import BeautifulSoup

# Aktifkan driver KML pada fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'

def ekstraksi_html_kml(text):
    """Membersihkan tag HTML dari kolom description KML."""
    if not isinstance(text, str):
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text(separator=" ").strip()

def bersihkan_angka_spd(val):
    """Mengubah format string 'Rp 22,917,302' menjadi float/int."""
    if str(val) == 'nan' or val is None:
        return 0.0
    val_str = str(val).replace("Rp", "").replace(".", "").replace(",", "").strip()
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def baca_kml(file_kml):
    """Membaca file KML dan mengidentifikasi kolom Name & SPD_JUNI."""
    if file_kml is None:
        return None
    try:
        gdf = gpd.read_file(file_kml, driver='KML')
        
        # 1. Ekstrak Nama Toko dari kolom 'Name' atau 'name'
        if 'Name' in gdf.columns:
            gdf['Nama_Toko'] = gdf['Name']
        elif 'name' in gdf.columns:
            gdf['Nama_Toko'] = gdf['name']
        else:
            gdf['Nama_Toko'] = gdf.iloc[:, 0]

        # 2. Cari Kolom SPD Terakhir (SPD_JUNI)
        spd_cols = [c for c in gdf.columns if c.startswith('SPD_')]
        if 'SPD_JUNI' in gdf.columns:
            kolom_spd_terakhir = 'SPD_JUNI'
        elif spd_cols:
            kolom_spd_terakhir = spd_cols[-1]
        else:
            kolom_spd_terakhir = None

        if kolom_spd_terakhir:
            gdf['SPD_Terakhir_Val'] = gdf[kolom_spd_terakhir].apply(bersihkan_angka_spd)
            gdf['SPD_Display'] = gdf[kolom_spd_terakhir].astype(str)
        else:
            gdf['SPD_Terakhir_Val'] = 0.0
            gdf['SPD_Display'] = "-"

        # 3. Clean Description
        if 'description' in gdf.columns:
            gdf['Detail_Info'] = gdf['description'].apply(ekstraksi_html_kml)
        else:
            gdf['Detail_Info'] = "-"

        return gdf
    except Exception as e:
        print(f"Error reading KML: {e}")
        return None

def hitung_fitur_dalam_radius(gdf, lat, lng, radius_meter):
    """Memfilter GeoDataFrame dan mengembalikan item yang hanya ada di dalam radius titik evaluasi."""
    if gdf is None or len(gdf) == 0:
        return 0, None

    # Titik pusat evaluasi
    center_gdf = gpd.GeoDataFrame(
        geometry=[Point(lng, lat)],
        crs="EPSG:4326"
    )

    # Reproyeksi ke UTM/Metric (EPSG:3857)
    center_metric = center_gdf.to_crs(epsg=3857)
    gdf_metric = gdf.to_crs(epsg=3857)

    # Lingkaran Buffer
    buffer_geom = center_metric.geometry.buffer(radius_meter).iloc[0]

    # Filter yang masuk radius
    gdf_filtered = gdf[gdf_metric.geometry.intersects(buffer_geom)]

    return len(gdf_filtered), gdf_filtered

def hitung_kepadatan_google_buildings(lat, lng, radius_meter):
    """Simulasi/Panggilan API Google Buildings dalam radius."""
    # Dummy logika penghitungan jumlah bangunan (sesuai fungsi terintegrasi sebelumnya)
    return 1245 

def kalkulasi_skor_potensi(bangunan, n_eksisting, n_kompetitor):
    """Menghitung skor potensi lokasi berdasarkan kriteria."""
    skor_bangunan = min((bangunan / 1500) * 50, 50)
    
    # Penalti/efek kompetitor
    if n_kompetitor == 0:
        skor_kompetitor = 30
    elif n_kompetitor <= 3:
        skor_kompetitor = 20
    else:
        skor_kompetitor = 10
        
    # Penalti/efek kanibalisasi toko eksisting
    if n_eksisting == 0:
        skor_eksisting = 20
    elif n_eksisting == 1:
        skor_eksisting = 15
    else:
        skor_eksisting = 5

    total_skor = int(skor_bangunan + skor_kompetitor + skor_eksisting)
    return total_skor, {"bangunan": skor_bangunan, "kompetitor": skor_kompetitor, "eksisting": skor_eksisting}
