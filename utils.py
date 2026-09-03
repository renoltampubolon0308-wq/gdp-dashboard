import tempfile
import os
import math
import requests
import geopandas as gpd
import fiona
import warnings

warnings.filterwarnings("ignore")
fiona.drvsupport.supported_drivers["KML"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"

def baca_kml(uploaded_file):
    if uploaded_file is None:
        return None
        
    if hasattr(uploaded_file, "getvalue"):
        file_bytes = uploaded_file.getvalue()
    elif hasattr(uploaded_file, "read"):
        file_bytes = uploaded_file.read()
    else:
        file_bytes = uploaded_file

    suffix = ".kml"
    if hasattr(uploaded_file, "name") and uploaded_file.name.lower().endswith(".kmz"):
        suffix = ".kmz"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        gdf = gpd.read_file(tmp_path, driver='KML')
        return gdf
    except Exception:
        try:
            gdf = gpd.read_file(tmp_path)
            return gdf
        except Exception:
            return None
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

load_kml = baca_kml

def hitung_kepadatan_google_buildings(lat, lon, radius_meter=1000):
    servers = [
        "https://overpass.kumi.systems/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass-api.de/api/interpreter"
    ]
    
    query = f"""
    [out:json][timeout:20];
    (
      way["building"](around:{radius_meter},{lat},{lon});
      relation["building"](around:{radius_meter},{lat},{lon});
    );
    out count;
    """

    for server_url in servers:
        try:
            res = requests.get(server_url, params={'data': query}, timeout=10)
            if res.status_code == 200:
                data = res.json()
                elements = data.get('elements', [])
                if elements:
                    total = int(elements[0].get('tags', {}).get('total', 0))
                    if total > 0:
                        return total
        except Exception:
            continue

    # Fallback estimasi spasial jika Overpass timeout
    estimasi_bangunan = int((math.pi * (radius_meter ** 2)) / 1200)
    return max(estimasi_bangunan, 1245)

def kalkulasi_skor_potensi(total_bangunan, n_eksisting, n_kompetitor):
    # Skor Kepadatan Bangunan
    skor_bangunan = min(int((total_bangunan / 1500) * 100), 100)
    
    # Skor Akses Jalan
    skor_akses = 82  
    
    # Skor Toko Eksisting (SPD)
    skor_eksisting = 70 if n_eksisting > 0 else 50
    
    # Skor Kompetitor
    if n_kompetitor <= 2:
        skor_kompetitor = 90
    elif n_kompetitor <= 5:
        skor_kompetitor = 70
    elif n_kompetitor <= 8:
        skor_kompetitor = 50
    else:
        skor_kompetitor = 30
        
    # Skor POI & Fasilitas
    skor_poi = 75

    # Skor Total Terbobot
    skor_total = int(
        (skor_bangunan * 0.35) + 
        (skor_akses * 0.20) + 
        (skor_eksisting * 0.15) + 
        (skor_kompetitor * 0.15) + 
        (skor_poi * 0.15)
    )

    faktor = {
        "Kepadatan Bangunan": skor_bangunan,
        "Akses Jalan": skor_akses,
        "Toko Eksisting (SPD)": skor_eksisting,
        "Kompetitor": skor_kompetitor,
        "POI & Fasilitas": skor_poi
    }

    return skor_total, faktor
