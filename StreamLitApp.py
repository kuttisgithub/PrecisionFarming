import streamlit as st
import time
import geocoder
from keras.preprocessing import image
from PrecisionFarming import PrecisionFarming

def update_city(lat, long):
    """Update the city and state based on latitude and longitude."""
    arc = geocoder.arcgis([lat, long], method="reverse")
    st.session_state.loc = f"{arc.city}, {arc.state}"

def update_lat_long(location):
    """Update the latitude and longitude based on the location."""
    st.session_state.lat, st.session_state.long = geocoder.arcgis(location).latlng

def create_streamlit_app():
    st.set_page_config(
        page_title="Precision Farming Assistant",
        page_icon="🌾",
        layout="wide"
    )

    st.title("🌾 Precision Farming Assistant")

    # Initialize session state
    if "pf" not in st.session_state:
        st.session_state.pf = PrecisionFarming()
    if "loc" not in st.session_state:
        st.session_state.loc = "Concord, NC"
        st.session_state.lat, st.session_state.long = geocoder.arcgis(st.session_state.loc).latlng

    # Location input
    loc = st.text_input("Location", key="loc", 
                       on_change=lambda: update_lat_long(st.session_state.loc))
    
    col1, col2 = st.columns(2)

    with col1:
        latitude = st.number_input("Latitude", value=st.session_state.lat, 
                                 on_change=lambda: update_city(st.session_state.lat, st.session_state.long))
        longitude = st.number_input("Longitude", value=st.session_state.long,
                                  on_change=lambda: update_city(st.session_state.lat, st.session_state.long))
        soil_ph = st.number_input("Soil pH", value=6.5, step=0.1)
        soil_moisture = st.number_input("Soil Moisture", value=30, step=1)

    with col2:
        area = st.number_input("Area (acres)", value=10, step=1)
        crop = st.selectbox("Select Crop", ["Corn", "Soybean", "Cotton"])
        insect = st.file_uploader("Upload Insect Image", type=["jpg", "png"])
        leaf = st.file_uploader("Upload Leaf Disease Image", type=["jpg", "png"])

    if st.button("Analyze Farm Conditions"):
        # Create containers for status updates
        status_area = st.container()
        progress_area = st.container()
        result_area = st.empty()

        # Dictionary to store progress bars for each tool
        tool_progress = {}

        def update_status(message, progress, tool_name):
            with status_area:
                if progress == -1:  # Error state
                    st.error(message)
                    return

                # Create or update tool-specific progress
                if tool_name not in tool_progress:
                    with progress_area:
                        tool_progress[tool_name] = {
                            'status': st.empty(),
                            'bar': st.progress(0)
                        }

                # Update status and progress
                prog = tool_progress[tool_name]
                prog['status'].info(f"{tool_name}: {message}")
                prog['bar'].progress(progress / 100)

                # Mark completion
                if progress == 100:
                    prog['status'].success(
                        f"{tool_name}: Completed at {time.strftime('%H:%M:%S')}"
                    )

        try:
            # Process images if provided
            insect_img = None
            leaf_img = None
            
            if insect:
                insect_img = image.load_img(insect, target_size=(224, 224))
            if leaf:
                leaf_img = image.load_img(leaf, target_size=(224, 224))

            # Get insights with progress tracking
            insights = st.session_state.pf.get_insights(
                soil_ph=soil_ph,
                soil_moisture=soil_moisture,
                latitude=latitude,
                longitude=longitude,
                area_acres=area,
                crop=crop,
                insect=insect_img,
                leaf=leaf_img,
                status_callback=update_status
            )

            # Display results
            result_area.markdown("### Farm Analysis Results")
            result_area.markdown(insights)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    create_streamlit_app()