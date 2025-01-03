import geocoder
from PrecisionFarming import PrecisionFarming
from flask import Flask, request, jsonify, send_file
from PIL import Image
from flasgger import Swagger
import io

# Initialize Flask app
app = Flask(__name__)
swagger = Swagger(app)

@app.route("/hello", methods=["GET"])
def hello():
    return "Hello Farming World!"    


@app.route('/leaf_disease', methods=['POST'])
def get_leaf_disease():
    try:
        # Check if the request contains a file
        if 'image' not in request.files:
            return jsonify({'error': 'No image file found in the request'}), 400
        data = request.form
        cropName = data.get('crop_name')
        if not cropName:
            return jsonify({'error': 'Missing required parameters'}), 400
        # Read the image file
        file = request.files['image']
        image = Image.open(file.stream)
        resized_image = image.resize((224, 224), Image.Resampling.NEAREST)
        pf = PrecisionFarming()
        leafdisease = pf.get_Leaf(resized_image, cropName)
        
        return leafdisease
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

TARGET_SIZE = (256, 256)

@app.route('/process-image', methods=['POST'])
def process_image():
    try:
        # Check for the image file
        if 'image' not in request.files:
            return jsonify({'error': 'No image file found in the request'}), 400

        # Check for the image type
        image_type = request.form.get('image_type')
        if not image_type:
            return jsonify({'error': 'No image type specified'}), 400

        # Read the image file
        file = request.files['image']
        image = Image.open(file.stream)

        # Resize the image to the target size
        resized_image = image.resize(TARGET_SIZE)

        # Process the image (e.g., convert to grayscale)
        processed_image = resized_image.convert('L')

        # Save the processed image to a BytesIO object
        img_io = io.BytesIO()
        processed_image.save(img_io, format=image_type.upper())  # Save using the specified type
        img_io.seek(0)

        # Send the processed image back as a response
        return send_file(img_io, mimetype=f'image/{image_type.lower()}')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/insects', methods=['POST'])
def get_insects():
    try:
        # Check if the request contains a file
        if 'image' not in request.files:
            return jsonify({'error': 'No image file found in the request'}), 400

        # Read the image file
        file = request.files['image']
        image = Image.open(file.stream)
        resized_image = image.resize((224, 224), Image.Resampling.NEAREST)
        pf = PrecisionFarming()
        leafdisease = pf.get_Insect(resized_image)
        
        return leafdisease
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    #app.run()
    app.run(host='0.0.0.0', port=80)

