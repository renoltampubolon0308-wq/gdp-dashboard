import math
import zipfile
import tempfile
import os
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

def load_kml_kmz(uploaded_file):
    """
    Fungsi universal untuk membaca file KML/KMZ menjadi GeoDataFrame.
    """
    if uploaded_file is None:
        return None
    
    filename = uploaded_file.name
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Jika file KMZ, ekstrak file KML di dalamnya
        if filename.endswith('.kmz'):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                    for file in os.listdir(tmpdir):
                        if file.endswith('.kml'):
                            file_path = os.path.join(tmpdir, file)
                            break
            except Exception:
                return None
        
        try:
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
            gdf = gpd.read_file(file_path, driver='KML')
            return gdf
        except Exception:
            return None

def hitung_kepadatan_per_ha(total_bangunan, radius_meter):
    """
    Hitung kepadatan bangunan per hektar berdasarkan luas lingkaran radius.
    """
    luas_m2 = math.pi * (radius_meter ** 2)
    luas_ha = luas_m2 / 10000.0  # 1 Ha = 10.000 m2
    
    kepadatan_ha = total_bangunan / luas_ha if luas_ha > 0 else 0
    
    if kepadatan_ha >= 60:
        kategori = "Tinggi (Padat)"
        skor = 25
    elif 40 <= kepadatan_ha < 60:
        kategori = "Sedang"
        skor = 18
    else:
        kategori = "Rendah"
        skor = 10
        
    return kepadatan_ha, kategori, skor

def kalkulasi_skor_potensi(lat, lng, radius_m, gdf_eksis=None, gdf_komp=None, gdf_bng=None, gdf_fasum=None):
    """
    Algoritma Skoring Hirarki Spasial Ritel.
    Parameter dibuat fleksibel/opsional untuk mencegah TypeError.
    """
    # 1. Hitung Bangunan Google dalam Radius
    point = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326")
    point_m = point.to_crs(epsg=3857)
    
    total_bng = 0
    if gdf_bng is not None and not gdf_bng.empty:
        gdf_bng_m = gdf_bng.to_crs(epsg=3857)
        bng_in_radius = gdf_bng_m[gdf_bng_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        total_bng = len(bng_in_radius)
        
    kepadatan_ha, kat_bng, skor_bng = hitung_kepadatan_per_ha(total_bng, radius_m)

    # 2. Hitung Fasum / Faskom (Money Traffic Generator - Auto Fetch Backend)
    skor_fasum = 10
    fasum_count = 0
    detail_fasum = "Auto-Fetch Spasial"
    if gdf_fasum is not None and not gdf_fasum.empty:
        gdf_fasum_m = gdf_fasum.to_crs(epsg=3857)
        fasum_in_radius = gdf_fasum_m[gdf_fasum_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        fasum_count = len(fasum_in_radius)
        if fasum_count > 0:
            text_combined = " ".join(fasum_in_radius['Name'].astype(str)).lower() if 'Name' in fasum_in_radius.columns else ""
            if any(k in text_combined for k in ['pasar', 'plaza', 'mall']):
                skor_fasum = 30
                detail_fasum = "Ada Pasar / Pusat Keramaian"
            elif any(k in text_combined for k in ['spbu', 'stasiun', 'terminal']):
                skor_fasum = 25
                detail_fasum = "Ada SPBU / Transit Hub"
            else:
                skor_fasum = 18
                detail_fasum = f"{fasum_count} Titik Fasum"

    # 3. Hitung Toko Eksis & SPD
    count_eksis = 0
    spd_eksis_val = 0
    if gdf_eksis is not None and not gdf_eksis.empty:
        gdf_eksis_m = gdf_eksis.to_crs(epsg=3857)
        eksis_in_radius = gdf_eksis_m[gdf_eksis_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        count_eksis = len(eksis_in_radius)
        for col in ['spd', 'SPD', 'sales', 'Sales']:
            if col in eksis_in_radius.columns:
                spd_eksis_val = pd.to_numeric(eksis_in_radius[col], errors='coerce').fillna(0).mean()
                break

    # 4. Hitung Kompetitor & SPD
    count_komp = 0
    spd_komp_val = 0
    if gdf_komp is not None and not gdf_komp.empty:
        gdf_komp_m = gdf_komp.to_crs(epsg=3857)
        komp_in_radius = gdf_komp_m[gdf_komp_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        count_komp = len(komp_in_radius)
        for col in ['spd', 'SPD', 'sales', 'Sales']:
            if col in komp_in_radius.columns:
                spd_komp_val = pd.to_numeric(komp_in_radius[col], errors='coerce').fillna(0).mean()
                break

    # Validasi Market Volume (Puncak SPD)
    avg_spd = max(spd_eksis_val, spd_komp_val)
    if avg_spd >= 12_500_000:
        skor_spd = 25
    elif avg_spd >= 8_000_000:
        skor_spd = 18
    else:
        skor_spd = 10

    # Skor Akses Jalan Baseline & Penalti
    skor_jalan = 20
    penalti = count_komp * 3
    
    # Total Skor
    total_skor = min(100, max(0, skor_bng + skor_fasum + skor_spd + skor_jalan - penalti))

    return {
        "skor_total": round(total_skor),
        "total_bng": total_bng,
        "kepadatan_ha": round(kepadatan_ha, 1),
        "kat_bng": kat_bng,
        "skor_bng": skor_bng,
        "fasum_count": fasum_count,
        "detail_fasum": detail_fasum,
        "skor_fasum": skor_fasum,
        "count_eksis": count_eksis,
        "spd_eksis_val": spd_eksis_val,
        "count_komp": count_komp,
        "spd_komp_val": spd_komp_val,
        "skor_spd": skor_spd,
        "skor_jalan": skor_jalan,
        "penalti": penalti
    }
