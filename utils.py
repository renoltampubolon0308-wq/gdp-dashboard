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
    try:
        overpass_url = "http://overpass-api.de/api/interpreter"
        query = f"""
        [out:json];
        (
          way["building"](around:{radius_meter},{lat},{lon});
          relation["building"](around:{radius_meter},{lat},{lon});
        );
        out count;
        """
        res = requests.get(overpass_url, params={'data': query}, timeout=15)
        data = res.json()
        
        elements = data.get('elements', [])
        total_bangunan = 0
        if elements:
            total_bangunan = int(elements[0].get('tags', {}).get('total', 0))
        
        # Estimasi rata-rata luas jejak bangunan (65 m² per unit)
        total_luas = total_bangunan * 65.0
        
        return total_bangunan, total_luas
    except Exception:
        return 0, 0
