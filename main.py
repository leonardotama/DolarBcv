from flask import Flask, jsonify
import requests
from bs4 import BeautifulSoup
import urllib3
import time

app = Flask(__name__)

# Configuración
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- MEMORIA CACHÉ (Aquí guardamos los datos) ---
cache = {
    "datos": None,      # Aquí se guardará el JSON con las tasas
    "ultima_actualizacion": 0  # Aquí guardaremos el "timestamp" de la última vez
}

# Tiempo de vida del caché en segundos (3600 segundos = 1 hora)
TIEMPO_EXPIRACION = 3600 

def obtener_tasas_bcv_real():
    """Esta función es la única que toca la web del BCV"""
    print("🔄 Conectando con el BCV para actualizar datos...") # Para que veas en consola cuando ocurre
    url = "https://www.bcv.org.ve/"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, verify=False, timeout=15, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            dolar = soup.find("div", {"id": "dolar"}).find("strong").text.strip()
            euro = soup.find("div", {"id": "euro"}).find("strong").text.strip()
            
            def limpiar(texto):
                return float(texto.replace(',', '.'))

            return {
                "fuente": "BCV (Oficial)",
                "timestamp": time.time(),
                "tasas": {
                    "USD": limpiar(dolar),
                    "EUR": limpiar(euro)
                }
            }
    except Exception as e:
        print(f"Error scraping: {e}")
        return None

@app.route('/api/tasas', methods=['GET'])
def get_tasas():
    ahora = time.time()
    
    # --- ESTRATEGIA DE CACHÉ ---
    # 1. ¿El caché está vacío? O
    # 2. ¿Ha pasado más de 1 hora desde la última vez?
    if cache["datos"] is None or (ahora - cache["ultima_actualizacion"] > TIEMPO_EXPIRACION):
        
        nuevos_datos = obtener_tasas_bcv_real()
        
        if nuevos_datos:
            # Si tuvimos éxito, actualizamos la memoria
            cache["datos"] = nuevos_datos
            cache["ultima_actualizacion"] = ahora
        else:
            # Si el BCV falló y tenemos datos viejos, mejor devolver los viejos que un error
            if cache["datos"] is None:
                return jsonify({"error": "BCV caído y no hay caché"}), 503
    
    # Devolvemos el dato guardado en memoria (es instantáneo)
    return jsonify({
        "data": cache["datos"],
        "cached": True, # Bandera para saber que no fuimos al BCV en esta consulta
        "proxima_actualizacion_en": int(TIEMPO_EXPIRACION - (ahora - cache["ultima_actualizacion"]))
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)