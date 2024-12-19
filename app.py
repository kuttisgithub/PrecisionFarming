import geocoder
from PrecisionFarming import PrecisionFarming
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

@app.route("/hello", methods=["GET"])
def hello():
    return "Hello Farming World!"    


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    location = data.get('location')
    crop = data.get('crop')
    soil_ph = data.get('soil_ph')
    soil_moisture = data.get('soil_moisture')

    if not location or not crop or soil_ph is None or soil_moisture is None:
        return jsonify({"error": "Missing required parameters"}), 400

    try:
        pf = PrecisionFarming()
        lat, long = geocoder.arcgis(location).latlng
        insights = pf.get_insights(
            soil_ph=soil_ph,
            soil_moisture=soil_moisture,
            latitude=lat,
            longitude=long,
            area_acres=10,  # Default value for area
            crop=crop,
            insect=None,
            leaf=None,
            status_callback=None
        )
        return jsonify({"status": "success", "insights": insights}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Run the Flask app
if __name__ == "__main__":
    app.run()

