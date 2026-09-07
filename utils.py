"""
Utilitas untuk Dashboard Potensi Lokasi Ritel.
Baca KML/KMZ, siapkan layer (cache + spatial index), dan hitung skor potensi lokasi.
"""

import os
import zipfile
import tempfile
import math

import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely.geometry import Point
import fiona

fiona.drvsupport.supported_drivers["KML"] = "rw"
fiona.drvsupport.supported_drivers["LIBKML"] = "rw"


# ---------------------------------------------------------------------------
# 1. BACA FILE KML / KMZ (dari Streamlit file_uploader)
# ---------------------------------------------------------------------------
def load_kml_kmz(uploaded_file):
    """Baca file KML/KMZ yang diupload lewat st.file_uploader. Return None kalau gagal/kosong."""
    if uploaded_file is None:
        return None

    try:
        nama_file = uploaded_file.name
        suffix = ".kmz" if nama_file.lower().endswith(".kmz") else ".kml"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        if suffix == ".kmz":
            extract_dir = tmp_path + "_extracted"
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(tmp_path, "r") as z:
                z.extractall(extract_dir)
            kml_inner = None
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith(".kml"):
                        kml_inner = os.path.join(root, f)
                        break
            if kml_inner is None:
                return None
            gdf = gpd.read_file(kml_inner, driver="KML")
        else:
            layers = fiona.listlayers(tmp_path)
            if len(layers) > 1:
                list_layer = []
                for layer in layers:
                    g = gpd.read_file(tmp_path, driver="KML", layer=layer)
                    g["_layer"] = layer
                    list_layer.append(g)
                gdf = pd.concat(list_layer, ignore_index=True)
                gdf = gpd.GeoDataFrame(gdf, geometry="geometry", crs="EPSG:4326")
            else:
                gdf = gpd.read_file(tmp_path, driver="KML")

        gdf = gdf[gdf.geometry.notna()].reset_index(drop=True)
        if gdf.crs is None:
            gdf = gdf.set_crs(epsg=4326)

        return gdf if len(gdf) > 0 else None

    except Exception:
        return None


# ---------------------------------------------------------------------------
# 2. SIAPKAN LAYER SEKALI SAJA (reproject + build spatial index) — DICACHE
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def siapkan_layer_meter(_gdf, cache_key):
    """Reproject ke EPSG:3857 & build spatial index, hanya dijalankan sekali per file
    berkat cache Streamlit (kunci cache = cache_key, bukan isi _gdf itu sendiri)."""
    if _gdf is None or _gdf.empty:
        return None
    gdf_m = _gdf.to_crs(epsg=3857).copy()
    gdf_m.sindex  # paksa build index di sini, sekali saja
    return gdf_m


def ambil_dalam_radius(gdf_m, point_m, radius_m):
    """Filter titik/garis dalam radius memakai spatial index dulu (cepat),
    baru hitung jarak presisi untuk kandidat yang lolos bounding box."""
    if gdf_m is None or gdf_m.empty:
        return gdf_m
    buffer = point_m.buffer(radius_m)
    idx = list(gdf_m.sindex.query(buffer, predicate="intersects"))
    if not idx:
        return gdf_m.iloc[0:0]
    subset = gdf_m.iloc[idx]
    jarak = subset.geometry.distance(point_m)
    return subset[jarak <= radius_m]


@st.cache_data(show_spinner="Mengambil data jalan dari OSM (sekali saja, lalu tersimpan)...")
def ambil_jalan_otomatis(base_dir, bbox_wsen):
    """Tarik jaringan jalan dari OSM untuk area (bbox), simpan ke parquet lokal supaya
    tidak perlu ditarik ulang tiap kali aplikasi dibuka. bbox_wsen = (west, south, east, north)."""
    import osmnx as ox

    path_jalan = os.path.join(base_dir, "data", "jalan.parquet")
    os.makedirs(os.path.join(base_dir, "data"), exist_ok=True)

    # kalau sudah pernah ditarik & mencakup area yang sama, pakai yang tersimpan
    if os.path.exists(path_jalan):
        try:
            return gpd.read_parquet(path_jalan)
        except Exception:
            pass

    tags_jalan = {"highway": ["primary", "secondary", "tertiary", "trunk", "trunk_link",
                               "primary_link", "secondary_link", "residential"]}
    try:
        gdf_jalan = ox.features_from_bbox(bbox=bbox_wsen, tags=tags_jalan)
        gdf_jalan = gdf_jalan[gdf_jalan.geometry.notna()]
        gdf_jalan = gdf_jalan[gdf_jalan.geometry.geom_type.isin(["LineString", "MultiLineString"])]
        gdf_jalan = gdf_jalan[["geometry"]].reset_index(drop=True)
        gdf_jalan.to_parquet(path_jalan)
        return gdf_jalan
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 3. DATASET LOKAL (parquet) — precomputed, tidak perlu query OSM/GEE live
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data_lokal(base_dir):
    """Load dataset lokal (bangunan, fasum, jalan) yang sudah di-precompute jadi parquet."""
    path_bng = os.path.join(base_dir, "data", "google_buildings.parquet")
    path_fasum = os.path.join(base_dir, "data", "fasum_faskom.parquet")
    path_jalan = os.path.join(base_dir, "data", "jalan.parquet")

    gdf_bng = gpd.read_parquet(path_bng) if os.path.exists(path_bng) else None
    gdf_fasum = gpd.read_parquet(path_fasum) if os.path.exists(path_fasum) else None
    gdf_jalan = gpd.read_parquet(path_jalan) if os.path.exists(path_jalan) else None
    return gdf_bng, gdf_fasum, gdf_jalan


# ---------------------------------------------------------------------------
# 4. KEPADATAN BANGUNAN -> kategori & skor
# ---------------------------------------------------------------------------
def hitung_kepadatan_per_ha(total_bng, radius_m):
    """Hitung kepadatan bangunan per hektar dalam radius, lalu kategorikan + beri skor (maks 25)."""
    luas_ha = (math.pi * radius_m ** 2) / 10000  # meter^2 -> hektar
    kepadatan_ha = total_bng / luas_ha if luas_ha > 0 else 0

    if kepadatan_ha >= 40:
        kategori, skor = "Sangat Padat", 25
    elif kepadatan_ha >= 25:
        kategori, skor = "Padat", 20
    elif kepadatan_ha >= 12:
        kategori, skor = "Sedang", 13
    elif kepadatan_ha >= 5:
        kategori, skor = "Jarang", 6
    else:
        kategori, skor = "Sangat Jarang", 0

    return kepadatan_ha, kategori, skor


# ---------------------------------------------------------------------------
# 5. SKORING UTAMA — pakai layer yang SUDAH direproject & di-index
# ---------------------------------------------------------------------------
def kalkulasi_skor_potensi(lat, lng, radius_m, gdf_eksis_m=None, gdf_komp_m=None,
                            gdf_bng_m=None, gdf_fasum_m=None, gdf_jalan_m=None):
    point_m = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326").to_crs(epsg=3857).iloc[0]

    # --- 1. Kepadatan bangunan (Google Open Buildings) ---
    bng_in_radius = ambil_dalam_radius(gdf_bng_m, point_m, radius_m)
    total_bng = len(bng_in_radius) if bng_in_radius is not None else 0
    kepadatan_ha, kat_bng, skor_bng = hitung_kepadatan_per_ha(total_bng, radius_m)

    # --- 2. Fasum / Faskom (match kata utuh, bukan substring) ---
    fasum_in_radius = ambil_dalam_radius(gdf_fasum_m, point_m, radius_m)
    fasum_count = len(fasum_in_radius) if fasum_in_radius is not None else 0
    skor_fasum, detail_fasum = 0, "Tidak Ada Fasum"

    if fasum_count > 0 and "Name" in fasum_in_radius.columns:
        kata_kata = set(" ".join(fasum_in_radius["Name"].astype(str)).lower().split())
        if kata_kata & {"pasar", "plaza", "mall"}:
            skor_fasum, detail_fasum = 30, "Ada Pasar / Pusat Keramaian"
        elif kata_kata & {"spbu", "stasiun", "terminal"}:
            skor_fasum, detail_fasum = 25, "Ada SPBU / Transit Hub"
        else:
            skor_fasum, detail_fasum = 18, f"{fasum_count} Titik Fasum"

    # --- 3. Toko eksisting (informasi saja, tidak memengaruhi skor) ---
    eksis_in_radius = ambil_dalam_radius(gdf_eksis_m, point_m, radius_m)
    count_eksis = len(eksis_in_radius) if eksis_in_radius is not None else 0

    # --- 4. Kompetitor: penalti berbasis JARAK, bukan cuma jumlah ---
    komp_in_radius = ambil_dalam_radius(gdf_komp_m, point_m, radius_m)
    count_komp = len(komp_in_radius) if komp_in_radius is not None else 0
    if count_komp > 0:
        jarak_semua = komp_in_radius.geometry.distance(point_m)
        penalti = sum(5 * max(0, 1 - (d / radius_m)) for d in jarak_semua)
        penalti = round(min(penalti, 40))
    else:
        penalti = 0

    # --- 5. Akses jalan: kepadatan jalan NYATA (bukan flat), fallback kalau layer belum ada ---
    if gdf_jalan_m is not None and not gdf_jalan_m.empty:
        jalan_in_radius = ambil_dalam_radius(gdf_jalan_m, point_m, radius_m)
        if jalan_in_radius is not None and len(jalan_in_radius) > 0:
            panjang_total = jalan_in_radius.geometry.intersection(point_m.buffer(radius_m)).length.sum()
            skor_jalan = round(min(20, (panjang_total / 3000) * 20))
        else:
            skor_jalan = 0
    else:
        skor_jalan = 15 if total_bng > 0 else 0

    # --- 6. SPD estimation (placeholder sampai ada data validasi pasar riil) ---
    skor_spd = 15 if total_bng > 0 else 0

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
        "count_komp": count_komp,
        "skor_spd": skor_spd,
        "skor_jalan": skor_jalan,
        "penalti": penalti,
    }
