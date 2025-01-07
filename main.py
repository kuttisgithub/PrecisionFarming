import io
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.openapi.utils import get_openapi
import geocoder
from PrecisionFarming import PrecisionFarming
from PIL import Image

app = FastAPI()

@app.post("/leaf_disease", summary="To Identify the leaf Disease.", description="To Identify the leaf Disease from the Uploaded leaf Image.")
async def Get_Leaf_Disease(file: UploadFile = File(...), crop_name: str = Form(...)):
    try:
        # Validate file content type
        print("CropName :=> " + crop_name)
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed.")

        # Read file content
        content = await file.read()

        # Convert the file content to an image
        try:
            image = Image.open(io.BytesIO(content))
            resized_image = image.resize((224, 224), Image.Resampling.NEAREST)
            pf = PrecisionFarming()
            leafdisease = pf.Identify_LeafDiseaseAndRecommendRemedies(resized_image, crop_name)
            image_format = image.format
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid image file.")

        return {
            "Disease": leafdisease[0],
            "Details": leafdisease[1],
            "crop_name": crop_name,
            "filename": file.filename,
            "content_type": file.content_type,
            "image_format": image_format
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/insects", summary="To Identify the leaf Disease.", description="To Identify the leaf Disease from the Uploaded leaf Image.")
async def Identify_Insects(file: UploadFile = File(...)):
    try:
        # Validate file content type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed.")

        # Read file content
        content = await file.read()

        # Convert the file content to an image
        try:
            image = Image.open(io.BytesIO(content))
            resized_image = image.resize((224, 224), Image.Resampling.NEAREST)
            pf = PrecisionFarming()
            insect = pf.get_Insect(resized_image)
        
            image_format = image.format
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid image file.")

        return {
            "Insect": insect,
            "filename": file.filename,
            "content_type": file.content_type,
            "image_format": image_format
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.post("/analyze", summary="To do the complete Analyzes", description="To do the complete Analyzes of the Soil, Crop, Location, Soil Ph and Soil Moisture.")
async def analyze(location: str = Form(...), crop: str = Form(...), soil_ph: float = Form(...), soil_moisture: float = Form(...)):

    if not location or not crop or soil_ph is None or soil_moisture is None:
         return {"error": "Missing required parameters"}, 400

    try:
        pf = PrecisionFarming()
        lat, long = geocoder.arcgis(location).latlng
        print("Latitude: ", lat)
        print("Longitude: ", long)
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
        
        return {"status": "success", "insights": insights}, 200
    
    except Exception as e:
        return {"error":  str(e)}, 500




@app.get("/hello", summary="Hello Farming World", description="Simple Hello World API")
async def hello():
    return "Hello Farming World!"    



def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="File Upload API",
        version="1.0.0",
        description="API for uploading and processing files",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
