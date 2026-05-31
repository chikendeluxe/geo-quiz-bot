"""
Génération d'images de carte avec geopandas + matplotlib.
Le pays cible est coloré en rouge sur fond sombre.
"""

import io
import asyncio
import warnings
from concurrent.futures import ThreadPoolExecutor

import matplotlib
matplotlib.use("Agg")  # Obligatoire avant l'import de pyplot en mode sans affichage
import matplotlib.pyplot as plt

_executor = ThreadPoolExecutor(max_workers=2)
_world_data = None  # Cache – chargé une seule fois

# Alias : notre nom → nom(s) dans geopandas (les versions diffèrent)
GEOPANDAS_ALIASES: dict[str, list[str]] = {
    "Turkey":                  ["Turkey", "Türkiye"],
    "S. Korea":                ["S. Korea", "South Korea"],
    "N. Korea":                ["N. Korea", "North Korea"],
    "Czechia":                 ["Czechia", "Czech Republic"],
    "Macedonia":               ["Macedonia", "North Macedonia"],
    "United States of America":["United States of America", "United States"],
    "Dem. Rep. Congo":         ["Dem. Rep. Congo", "Democratic Republic of the Congo"],
    "Bosnia and Herz.":        ["Bosnia and Herz.", "Bosnia and Herzegovina"],
}


def _load_world():
    """Charge le GeoDataFrame monde (avec cache)."""
    global _world_data
    if _world_data is not None:
        return _world_data

    import geopandas as gpd

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # 1. API moderne (geodatasets, geopandas ≥ 1.0)
        try:
            import geodatasets
            _world_data = gpd.read_file(geodatasets.get_path("naturalearth lowres"))
            return _world_data
        except Exception:
            pass

        # 2. API legacy (geopandas < 1.0)
        try:
            _world_data = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
            return _world_data
        except Exception:
            pass

    raise RuntimeError(
        "Impossible de charger les données cartographiques. "
        "Installez 'geodatasets' : pip install geodatasets"
    )


def _find_country(world, name: str):
    """Cherche un pays dans le GeoDataFrame, en essayant les alias."""
    result = world[world.name == name]
    if not result.empty:
        return result

    for alias in GEOPANDAS_ALIASES.get(name, []):
        result = world[world.name == alias]
        if not result.empty:
            return result

    # Dernier recours : insensible à la casse
    result = world[world.name.str.lower() == name.lower()]
    return result


def _generate_map_sync(country_name_en: str) -> bytes:
    """Version synchrone de la génération de carte (appelée dans un thread)."""
    world = _load_world()
    target = _find_country(world, country_name_en)

    if target.empty:
        raise ValueError(f"Pays '{country_name_en}' introuvable dans le dataset.")

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_facecolor("#0d2137")          # Océan bleu nuit
    fig.patch.set_facecolor("#06111e")   # Fond de la figure

    # Tous les pays en vert foncé
    world.plot(ax=ax, color="#1e3d20", edgecolor="#3a6e3a", linewidth=0.35)
    # Pays cible en rouge vif
    target.plot(ax=ax, color="#e63946", edgecolor="#ff8fa3", linewidth=1.5)

    # Calcul du zoom avec padding adaptatif
    bounds = target.geometry.total_bounds  # [minx, miny, maxx, maxy]
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    pad = max(w, h, 4.0) * 0.9           # au moins 4° de marge

    xlim = (max(-180.0, bounds[0] - pad), min(180.0, bounds[2] + pad))
    ylim = (max(-90.0,  bounds[1] - pad), min(90.0,  bounds[3] + pad))

    # Correction du ratio (évite une image trop étroite ou trop plate)
    xr = xlim[1] - xlim[0]
    yr = ylim[1] - ylim[0]
    if xr / max(yr, 0.1) > 3.0:
        mid = (ylim[0] + ylim[1]) / 2
        half = xr / 3.0 / 2
        ylim = (max(-90.0, mid - half), min(90.0, mid + half))
    elif yr / max(xr, 0.1) > 3.0:
        mid = (xlim[0] + xlim[1]) / 2
        half = yr * 3.0 / 2
        xlim = (max(-180.0, mid - half), min(180.0, mid + half))

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.axis("off")

    buf = io.BytesIO()
    plt.savefig(
        buf, format="png", dpi=130,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor="none",
    )
    buf.seek(0)
    plt.close(fig)
    return buf.getvalue()


async def generate_country_map(country_name_en: str) -> io.BytesIO:
    """Génère une carte de façon asynchrone (non-bloquant pour le bot)."""
    loop = asyncio.get_event_loop()
    img_bytes = await loop.run_in_executor(
        _executor, _generate_map_sync, country_name_en
    )
    return io.BytesIO(img_bytes)
