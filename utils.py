import zipfile
import tempfile
import os
import math
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon, MultiPoint

def drop_z(geometry):
    """
    Menghapus koordinat Z (3D menjadi 2D) agar kompatibel dengan Folium & Shapely.
    """
    if geometry is None:
        return None
    if geometry.has_z:
        if geometry.geom_type == 'Point':
            return Point(geometry.x, geometry.y)
        elif geometry.geom_type == 'LineString':
            return LineString([(p[0], p[1]) for p in geometry.coords])
        elif geometry.geom_type == 'Polygon':
            lines = [LineString([(p[0], p[1]) for p in geometry.exterior.coords])]
            return Polygon(lines[0])
    return geometry

def load_kml_kmz(uploaded_file):
    """
    Membaca file KML/KMZ dari Streamlit FileUploader dan mengembalikan GeoDataFrame (EPSG:4326).
    """
    if uploaded_file is None:
        return None
    
    filename = uploaded_file.name
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, filename)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        target_kml = file_path
        if filename.lower().endswith('.kmz'):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                    for root, dirs, files in os.walk(tmpdir):
                        for file in files:
                            if file.lower().endswith('.kml'):
                                target_kml = os.path.join(root, file)
                                break
            except Exception:
                return None
        
        try:
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
            gpd.io.file.fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'
            
            gdf = gpd.read_file(target_kml)
            
            if gdf.empty:
                return None
                
            # Konversi Z (3D) ke 2D
            gdf['geometry'] = gdf['geometry'].apply(drop_z)
            
            # Memastikan CRS terdaftar sebagai WGS84
            if gdf.crs is None:
                gdf.set_crs(epsg=4326, inplace=True)
            else:
                gdf = gdf.to_crs(epsg=4326)
                
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
    """
    point = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326")
    point_m = point.to_crs(epsg=3857)
    
    # 1. Kepadatan Bangunan Google Open Buildings
    total_bng = 0
    if gdf_bng is not None and not gdf_bng.empty:
        gdf_bng_m = gdf_bng.to_crs(epsg=3857)
        bng_in_radius = gdf_bng_m[gdf_bng_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        total_bng = len(bng_in_radius)
        
    kepadatan_ha, kat_bng, skor_bng = hitung_kepadatan_per_ha(total_bng, radius_m)

    # 2. Fasum / Faskom (Money Traffic Generator)
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

    # 3. Toko Eksis & SPD
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

    # 4. Kompetitor & SPD
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

    avg_spd = max(spd_eksis_val, spd_komp_val)
    if avg_spd >= 12_500_000:
        skor_spd = 25
    elif avg_spd >= 8_000_000:
        skor_spd = 18
    else:
        skor_spd = 10

    skor_jalan = 20
    penalti = count_komp * 3
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
