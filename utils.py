def kalkulasi_skor_potensi(lat, lng, radius_m, gdf_eksis=None, gdf_komp=None, gdf_bng=None, gdf_fasum=None):
    point = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326")
    point_m = point.to_crs(epsg=3857)
    
    # 1. Kepadatan Bangunan (Google Open Buildings)
    total_bng = 0
    if gdf_bng is not None and not gdf_bng.empty:
        gdf_bng_m = gdf_bng.to_crs(epsg=3857)
        bng_in_radius = gdf_bng_m[gdf_bng_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        total_bng = len(bng_in_radius)

    kepadatan_ha, kat_bng, skor_bng = hitung_kepadatan_per_ha(total_bng, radius_m)

    # 2. Fasum / Faskom
    skor_fasum = 0
    fasum_count = 0
    detail_fasum = "Tidak Ada Fasum"
    
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

    # 3. Toko Eksisting
    count_eksis = 0
    if gdf_eksis is not None and not gdf_eksis.empty:
        gdf_eksis_m = gdf_eksis.to_crs(epsg=3857)
        eksis_in_radius = gdf_eksis_m[gdf_eksis_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        count_eksis = len(eksis_in_radius)

    # 4. Toko Kompetitor
    count_komp = 0
    if gdf_komp is not None and not gdf_komp.empty:
        gdf_komp_m = gdf_komp.to_crs(epsg=3857)
        komp_in_radius = gdf_komp_m[gdf_komp_m.geometry.distance(point_m.iloc[0]) <= radius_m]
        count_komp = len(komp_in_radius)

    # Nilai dasar jalan & spd hanya jika ada minimal bangunan/fasum
    skor_spd = 15 if total_bng > 0 else 0
    skor_jalan = 15 if total_bng > 0 else 0
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
        "spd_eksis_val": 0,
        "count_komp": count_komp,
        "spd_komp_val": 0,
        "skor_spd": skor_spd,
        "skor_jalan": skor_jalan,
        "penalti": penalti
    }
