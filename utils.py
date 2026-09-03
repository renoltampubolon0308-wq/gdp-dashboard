import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point
import fiona

# Mengaktifkan support driver KML pada fiona
fiona.drvsupport.supported_drivers['KML'] = 'rw'
fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'


def baca_kml(uploaded_file):
    """
    Membaca file KML / GeoJSON / Zip yang diupload user 
    dan mengembalikannya sebagai GeoDataFrame dengan CRS EPSG:4326.
    """
    if uploaded_file is None:
        return None
    
    try:
        # Coba baca langsung menggunakan GeoPandas
        gdf = gpd.read_file(uploaded_file)
        
        # Pastikan CRS diset ke WGS84 (EPSG:4326)
        if gdf.crs is None:
            gdf.set_crs(epsg=4326, inplace=True)
        else:
            gdf = gdf.to_crs(epsg=4326)
            
        return gdf
    except Exception as e:
        print(f"Error membaca file spatial: {e}")
        return None


def hitung_kepadatan_google_buildings(gdf_buildings, lat, lng, radius_meter):
    """
    Menghitung jumlah polygon/titik bangunan dari GeoDataFrame (Google Buildings)
    yang berada di dalam radius buffer (dalam meter) dari koordinat (lat, lng).
    """
    if gdf_buildings is None or len(gdf_buildings) == 0:
        return 0

    try:
        # Buat GeoDataFrame untuk titik pusat evaluasi
        center_gdf = gpd.GeoDataFrame(
            geometry=[Point(lng, lat)],
            crs="EPSG:4326"
        )

        # Reproyeksi ke CRS Proyeksi Meter (EPSG:3857) agar jarak radius presisi
        center_metric = center_gdf.to_crs(epsg=3857)
        gdf_metric = gdf_buildings.to_crs(epsg=3857)

        # Buat lingkaran buffer berdasarkan radius_meter terpilih
        buffer_geom = center_metric.geometry.buffer(radius_meter).iloc[0]

        # Filter dan hitung bangunan yang berada/berpotongan di dalam buffer
        gdf_filtered = gdf_buildings[gdf_metric.geometry.intersects(buffer_geom)]

        return len(gdf_filtered)
    except Exception as e:
        print(f"Error saat menghitung spatial buffer: {e}")
        return 0


def hitung_poin_radius(gdf_points, lat, lng, radius_meter):
    """
    Menghitung jumlah titik (Eksisting / Kompetitor) dalam radius buffer.
    """
    if gdf_points is None or len(gdf_points) == 0:
        return 0
    
    try:
        center_gdf = gpd.GeoDataFrame(geometry=[Point(lng, lat)], crs="EPSG:4326")
        center_metric = center_gdf.to_crs(epsg=3857)
        gdf_metric = gdf_points.to_crs(epsg=3857)
        
        buffer_geom = center_metric.geometry.buffer(radius_meter).iloc[0]
        gdf_filtered = gdf_points[gdf_metric.geometry.intersects(buffer_geom)]
        return len(gdf_filtered)
    except Exception:
        return 0


def kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor):
    """
    Menghitung Skor Potensi (0 - 100) berdasarkan jumlah bangunan, toko eksisting, dan kompetitor.
    
    Bobot Penilaian:
    1. Kepadatan Bangunan (Max 50 Poin)
    2. Tingkat Kompetisi (Max 30 Poin)
    3. Kanibalisasi / Toko Eksisting (Max 20 Poin)
    """
    # 1. Bobot Kepadatan Bangunan (0 - 50)
    # Patokan: >= 1000 bangunan = Poin Maksimal (50)
    skor_bangunan = min(50, (total_bangunan / 1000) * 50)

    # 2. Bobot Kompetitor (0 - 30) -> Makin sedikit kompetitor, skor makin tinggi
    if n_kompetitor == 0:
        skor_kompetitor = 30
    elif n_kompetitor <= 2:
        skor_kompetitor = 20
    elif n_kompetitor <= 5:
        skor_kompetitor = 10
    else:
        skor_kompetitor = 0

    # 3. Bobot Eksisting / Kanibalisasi (0 - 20) -> Makin sedikit toko eksisting, skor makin tinggi
    if n_eksisting == 0:
        skor_eksisting = 20
    elif n_eksisting == 1:
        skor_eksisting = 10
    else:
        skor_eksisting = 0

    # Total Skor
    skor_total = int(round(skor_bangunan + skor_kompetitor + skor_eksisting))
    
    # Keterangan Faktor Penilaian
    faktor = {
        "Skor Bangunan": round(skor_bangunan, 1),
        "Skor Kompetitor": skor_kompetitor,
        "Skor Eksisting": skor_eksisting
    }

    return skor_total, faktor
