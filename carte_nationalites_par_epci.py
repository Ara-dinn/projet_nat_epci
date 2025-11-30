# carte_nationalites_par_epci.py

from flask import Flask, render_template, request, make_response
import pandas as pd
import geopandas as gpd
import json
import folium
from sqlalchemy import create_engine
import logging


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Accès DB ---
engine = create_engine("postgresql://postgres:postgres@localhost/savoie")

# --- Selection des données ---
# J'ai traité les données pour ne garder que les étrangers
query = """
SELECT 
    "EPCI",
    "nom_epci",
    "NAT_rec3" AS "Nationalite",
    "total_s",
    "part_etrg_epci",
    "geometry"
FROM poisson.nat_etrg_par_epci
"""
geo_df = gpd.read_postgis(query, engine, geom_col="geometry")# adapté à GeoDataFrame
#geo_df = geo_df.dropna(subset=["part_etrg_epci"])

# Ressources

# --- Page ou route principale ---
@app.route("/nationalites_epci")
def index():
    Nationalite = sorted(geo_df["Nationalite"].unique())  # liste des nationalités
    return render_template("carte_nat_bis.html", Nationalite=Nationalite)


# --- Route pour générer la carte ---
@app.route("/get_data_plot")
def get_data_plot():
    nat = request.args.get("Nationalite", "")  # récupère la nationalite choisie
    
    # Filtrer le GeoDataFrame pour la région sélectionnée
    geo_nationalite = geo_df[geo_df["Nationalite"] == nat]
    
    if geo_nationalite.empty:
        return make_response(
            json.dumps({"error": "Pas de données pour cette nationalité"}),
            200,
            {"Content-Type": "application/json"}
        )
    # Centrer la carte sur la région (coordonnées approximatives)
    # Création de la carte centrée sur la France
    m = folium.Map(
        location=[46.6, 2.5], 
        zoom_start=6,
        tiles="cartodbpositron"
    )
     # Calque choroplèthe pour la nationalité choisie
    folium.Choropleth(
        geo_data=geo_nationalite,
        name=f"Part {nat}",
        data=geo_nationalite,
        columns=["EPCI", "part_etrg_epci"],
        key_on="feature.properties.EPCI",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.3,
        line_weight=0.2,
        legend_name=f"Part de {nat} (%)"
    ).add_to(m)
    
    # Ajouter info-bulles
    folium.GeoJson(
        geo_nationalite,
        name="Infos",
        tooltip=folium.features.GeoJsonTooltip(
            fields=["nom_epci", "part_etrg_epci", 'total_s'],
            aliases=["EPCI :", "Part (%) :", "Fréquence absolue :"],
            localize=True
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    # Retourner le HTML de la carte
    map_html = m._repr_html_()
    return make_response(
        json.dumps({"map_html": map_html}),
        200,
        {"Content-Type": "application/json"}
    )
    
if __name__ == "__main__":
    app.run(debug=True)
    
    
