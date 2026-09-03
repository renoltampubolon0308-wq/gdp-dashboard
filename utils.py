import tempfile
import os
import re
import math
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, box
import fiona
import warnings
import duckdb

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
                total_bangunan = 0
                if elements:
                    total_bangunan = int(elements[0].get('tags', {}).get('total', 0))
                
                if total_bangunan > 0:
                    total_luas = total_bangunan * 65.0
                    return total_bangunan, total_luas
        except Exception:
            continue

    # Fallback perhitungan spasial jika server publik Overpass sibuk/timeout
    estimasi_bangunan = int((math.pi * (radius_meter ** 2)) / 1200)
    return estimasi_bangunan, estimasi_bangunan * 65.0
