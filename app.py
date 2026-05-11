from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import requests
import json
import os

app = Flask(__name__)
CORS(app)

# Configura tu API KEY de Google Cloud desde config.json
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.json')
try:
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        GOOGLE_API_KEY = config.get("GOOGLE_MAPS_KEY", "TU_API_KEY_AQUI")
except Exception as e:
    print(f"Error al cargar config.json: {e}")
    GOOGLE_API_KEY = "TU_API_KEY_AQUI"

def obtener_datos_catastro(rc):
    """
    Obtiene coordenadas y tipo de inmueble usando el servicio JSON de la OVC.
    """
    rc_finca = rc[:14]
    url = f"https://ovc.catastro.meh.es/OVCServWeb/OVCWcfCallejero/COVCCoordenadas.svc/json/Consulta_CPMRC?SRS=EPSG:4326&RefCat={rc_finca}"
    
    try:
        # Aunque es un servicio más moderno, a veces meh.es también requiere verify=False en entornos locales
        response = requests.get(url, verify=False)
        data = response.json()
        
        # Extraer datos del JSON según la estructura recibida
        resultado = data.get('Consulta_CPMRCResult', {})
        coordenadas = resultado.get('coordenadas', {}).get('coord', [])
        
        if not coordenadas:
            return None
            
        coord_data = coordenadas[0]
        geo = coord_data.get('geo', {})
        
        # En el Catastro con EPSG:4326, xcen es Longitud e ycen es Latitud
        lon = geo.get('xcen')
        lat = geo.get('ycen')
        
        if not lat or not lon:
            return None

        # Determinar si es Urbana o Rústica según la RC
        tipo = "URBANA" if len(rc) == 20 and not rc[2:5].isdigit() else "RUSTICA"
        
        return {
            "lat": lat,
            "lon": lon,
            "tipo": tipo
        }
    except Exception as e:
        print(f"Error en la consulta: {e}")
        return None

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/inmueble/<rc>')
def get_inmueble_image(rc):
    datos = obtener_datos_catastro(rc)
    
    if not datos:
        return jsonify({"error": "Referencia catastral no encontrada"}), 404

    lat, lon = datos['lat'], datos['lon']
    
    # Paso 2: Lógica de imagen según tipo de inmueble
    if datos['tipo'] == "RUSTICA":
        # Imagen de Satélite para fincas rústicas
        image_url = f"https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom=17&size=600x400&maptype=satellite&markers=color:red%7C{lat},{lon}&key={GOOGLE_API_KEY}"
    else:
        # Street View para inmuebles urbanos
        image_url = f"https://maps.googleapis.com/maps/api/streetview?size=600x400&location={lat},{lon}&key={GOOGLE_API_KEY}"

    return jsonify({
        "referencia": rc,
        "tipo": datos['tipo'],
        "coordenadas": {"lat": lat, "lon": lon},
        "url_imagen": image_url
    })

if __name__ == '__main__':
    app.run(debug=True)