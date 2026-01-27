from flask import Flask, jsonify
from flask_cors import CORS  # <--- 1. Importamos la llave
import requests
from bs4 import BeautifulSoup
import urllib3
import time

app = Flask(__name__)
CORS(app)  # <--- 2. ¡Abrimos el candado! Esto permite que tu web lea los datos.

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- MEMORIA CACHÉ ---
cache = {
    "datos": None,
    "ultima_actualizacion": 0
}
TIEMPO_EXPIRACION = 3600  # 1 hora

def obtener_tasas_bcv_real():
    print("🔄 Conectando con el BCV...")
    url = "https://www.bcv.org.ve/"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, verify=False, timeout=15, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            dolar = soup.find("div", {"id": "dolar"}).find("strong").text.strip()
            euro = soup.find("div", {"id": "euro"}).find("strong").text.strip()
            
            # Buscar fecha
            fecha_tag = soup.find("span", {"class": "date-display-single"})
            fecha_texto = fecha_tag.text.strip() if fecha_tag else "Fecha no encontrada"

            def limpiar(texto):
                return float(texto.replace(',', '.'))

            return {
                "fuente": "Banco Central de Venezuela",
                "fecha_valor": fecha_texto,
                "timestamp_consulta": time.time(),
                "tasas": {
                    "USD": { "nombre": "Dólar", "valor": limpiar(dolar), "simbolo": "$" },
                    "EUR": { "nombre": "Euro", "valor": limpiar(euro), "simbolo": "€" }
                }
            }
    except Exception as e:
        print(f"Error scraping: {e}")
        return None

# --- RUTAS ---

@app.route('/')
def index():
    return jsonify({
        "estado": "Activo 🟢",
        "mensaje": "La API funciona. CORS activado."
    })

@app.route('/api/tasas', methods=['GET'])
def get_tasas():
    ahora = time.time()
    
    if cache["datos"] is None or (ahora - cache["ultima_actualizacion"] > TIEMPO_EXPIRACION):
        nuevos_datos = obtener_tasas_bcv_real()
        if nuevos_datos:
            cache["datos"] = nuevos_datos
            cache["ultima_actualizacion"] = ahora
        else:
            if cache["datos"] is None:
                return jsonify({"error": "BCV no responde"}), 503
    
    return jsonify({
        "data": cache["datos"],
        "cached": True
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
