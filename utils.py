import tempfile
import os
import re
import math
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
    """
    Membaca file KML/KMZ yang diunggah via Streamlit uploader.
    """
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

# Alias agar kompatibel jika dipanggil dengan nama load_kml
load_kml = baca_kml

def hitung_kepadatan_google_buildings(lat, lon, radius_meter=500):
    """
    Menghitung jumlah & total luas footprint bangunan Google Open Buildings.
    """
    try:
        con = duckdb.connect()
        query = f"""
        SELECT id, geometry, area_in_meters
        FROM read_parquet('s3://open-buildings-data/v3/polygons/*.parquet')
        WHERE ST_Within(
            ST_GeomFromText(geometry),
            ST_Buffer(ST_Point({lon}, {lat}), {radius_meter / 111000.0})
        )
        """
        df_buildings = con.execute(query).df()
        total_bangunan = len(df_buildings)
        total_luas = df_buildings['area_in_meters'].sum() if not df_buildings.empty else 0
        return total_bangunan, total_luas
    except Exception:
        return 0, 0
