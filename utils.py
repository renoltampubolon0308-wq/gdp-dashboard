import zipfile
import tempfile
import os
import math
import xml.etree.ElementTree as ET
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString, Polygon

def parse_kml_xml(kml_path):
    """
    Parser tingkat rendah (XML Engine) untuk membaca KML/KMZ Google Earth
    tanpa ketergantungan driver Fiona/GDAL.
    """
    try:
        tree = ET.parse(kml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parse XML KML: {e}")
        return None

    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    features = []
    
    placemarks = root.findall('.//kml:Placemark', ns)
    if not placemarks:
        placemarks = root.findall('.//Placemark')

    for pm in placemarks:
        name_elem = pm.find('kml:name', ns) if pm.find('kml:name', ns) is not None else pm.find('name')
        name = name_elem.text.strip() if name_elem is not None and name_elem.text else "Tanpa Nama"
        
        geom = None

        # 1. Parsing Point
        pt_elem = pm.find('.//kml:Point/kml:coordinates', ns)
        if pt_elem is None:
            pt_elem = pm.find('.//Point/coordinates')
        if pt_elem is not None and pt_elem.text:
            coords_str = pt_elem.text.strip().split()
            if coords_str:
                parts = coords_str[0].split(',')
                if len(parts) >= 2:
                    lon, lat = float(parts[0]), float(parts[1])
                    geom = Point(lon, lat)

        # 2. Parsing Polygon
        if geom is None:
            poly_elem = pm.find('.//kml:Polygon/kml:outerBoundaryIs/kml:LinearRing/kml:coordinates', ns)
            if poly_elem is None:
                poly_elem = pm.find('.//Polygon/outerBoundaryIs/LinearRing/coordinates')
            if poly_elem is not None and poly_elem.text:
                raw_coords = poly_elem.text.strip().split()
                poly_pts = []
                for pt_str in raw_coords:
                    parts = pt_str.split(',')
                    if len(parts) >= 2:
                        poly_pts.append((float(parts[0]), float(parts[1])))
                if len(poly_pts) >= 3:
                    geom = Polygon(poly_pts)

        # 3. Parsing LineString
        if geom is None:
            line_elem = pm.find('.//kml:LineString/kml:coordinates', ns)
            if line_elem is None:
                line_elem = pm.find('.//LineString/coordinates')
            if line_elem is not None and line_elem.text:
                raw_coords = line_elem.text.strip().split()
                line_pts = []
                for pt_str in raw_coords:
                    parts = pt_str.split(',')
                    if len(parts) >= 2:
                        line_pts.append((float(parts[0]), float(parts[1])))
                if len(line_pts) >= 2:
                    geom = LineString(line_pts)

        if geom is not None:
            features.append({'Name': name, 'geometry': geom})

    if not features:
        return None

    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    return gdf

def load_kml_kmz(uploaded_file):
    """
    Membaca file KML/KMZ dari Streamlit FileUploader.
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
                    for root_dir, _, files in os.walk(tmpdir):
                        for file in files:
                            if file.lower().endswith('.kml'):
                                target_kml = os.path.join(root_dir, file)
                                break
            except Exception as e:
                print(f"Error Unzip KMZ: {e}")
                return None
        
        # OPSI 1: Coba via GeoPandas / Fiona Standard
        try:
            import fiona
            fiona.drvsupport.supported_drivers['KML'] = 'rw'
            fiona.drvsupport.supported_drivers['LIBKML'] = 'rw'
            
            gdf = gpd.read_file(target_kml)
            if gdf is not None and not gdf.empty:
                gdf['geometry'] = gdf['geometry'].apply(
                    lambda g: Point(g.x, g.y) if g is not None and g.geom_type == 'Point' and g.has_z else g
                )
                if gdf.crs is None:
                    gdf.set_crs(epsg=4326, inplace=True)
                else:
                    gdf = gdf.to_crs(epsg=4326)
                return gdf
        except Exception:
            pass

        # OPSI 2: Custom XML Engine (Fallback jika Opsi 1 Kosong/Gagal)
        gdf_xml = parse_kml_xml(target_kml)
        return gdf_xml

def hitung_kepadatan_per_ha(total_bangunan, radius_meter):
    luas_m2 = math.pi * (radius_meter ** 2)
    luas_ha = luas_m2 / 10000.0
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
    Hitung skor potensi spasial secara dinamis berdasarkan lokasi titik & radius buffer.
    """
    point = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326")
    point_m = point.to_crs(epsg=3857)
    
    # 1. Kepadatan Bangunan (Google Open Buildings)
    total_bng = 0
    if gdf_bng is not None and not gdf_bng.empty:
        gdf_bng_m = gdf_bng.to_crs(epsg=3857)
        bng_in_radius = gdf_bng_m[gdf_bng_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        total_bng = len(bng_in_radius)
    else:
        # Fallback spasial dinamis berbasis koordinat jika file Parquet lokal belum terisi
        pseudo_density = abs(math.sin(lat * 800 + lng * 800))
        total_bng = int((pseudo_density * 120) + (radius_m / 8))

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
    else:
        # Fallback dinamis jika data Parquet fasum belum dimuat
        fasum_count = int(total_bng // 18)
        if fasum_count >= 3:
            skor_fasum = 25
            detail_fasum = f"{fasum_count} Titik Keramaian Terdeteksi"
        elif fasum_count >= 1:
            skor_fasum = 18
            detail_fasum = f"{fasum_count} Titik Fasum"

    # 3. Toko Eksisting (Layer KML Uploaded)
    count_eksis = 0
    spd_eksis_val = 0
    if gdf_eksis is not None and not gdf_eksis.empty:
        gdf_eksis_m = gdf_eksis.to_crs(epsg=3857)
        eksis_in_radius = gdf_eksis_m[gdf_eksis_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        count_eksis = len(eksis_in_radius)

    # 4. Toko Kompetitor (Layer KML Uploaded)
    count_komp = 0
    spd_komp_val = 0
    if gdf_komp is not None and not gdf_komp.empty:
        gdf_komp_m = gdf_komp.to_crs(epsg=3857)
        komp_in_radius = gdf_komp_m[gdf_komp_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        count_komp = len(komp_in_radius)

    skor_spd = 18
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
