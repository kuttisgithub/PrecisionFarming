import streamlit as st
import time
import geocoder
from keras.preprocessing import image
from PrecisionFarming import PrecisionFarming

def show_completion_animation():
    """Show a farming-themed emoji animation."""
    success_emojis = ["🌱", "🌿", "🌾", "🎋", "✨"]
    animation_placeholder = st.empty()
    for emoji in success_emojis:
        animation_placeholder.markdown(
            f"<h1 style='text-align: center'>{emoji}</h1>", 
            unsafe_allow_html=True
        )
        time.sleep(0.3)
    animation_placeholder.empty()

def update_city(lat, long):
    """Update the city and state based on latitude and longitude."""
    arc = geocoder.arcgis([lat, long], method="reverse")
    st.session_state.loc = f"{arc.city}, {arc.state}"

def update_lat_long(location):
    """Update the latitude and longitude based on the location."""
    st.session_state.lat, st.session_state.long = geocoder.arcgis(
        location).latlng

def create_streamlit_app():
    st.set_page_config(page_title="Precision Farming Assistant",
                       page_icon="🌾",
                       layout="wide")

    st.title("🌾 Precision Farming Assistant")

    if "pf" not in st.session_state:
        st.session_state.pf = PrecisionFarming()
    if "loc" not in st.session_state:
        st.session_state.loc = "Concord, NC"
        st.session_state.lat, st.session_state.long = geocoder.arcgis(
            st.session_state.loc).latlng

    input_col, status_col = st.columns([1, 2])

    with input_col:
        st.header("Input Parameters")
        
        loc = st.text_input("Location", 
                           key="loc",
                           on_change=lambda: update_lat_long(st.session_state.loc))
        
        lat_col, long_col = st.columns(2)
        with lat_col:
            latitude = st.number_input("Latitude",
                                     value=st.session_state.lat,
                                     on_change=lambda: update_city(
                                         st.session_state.lat,
                                         st.session_state.long))
        with long_col:
            longitude = st.number_input("Longitude",
                                      value=st.session_state.long,
                                      on_change=lambda: update_city(
                                          st.session_state.lat,
                                          st.session_state.long))

        area = st.number_input("Area (acres)", min_value=1, value=10)
        soil_ph = st.slider("Soil pH", 0.0, 14.0, 6.5, 0.1)
        soil_moisture = st.slider("Soil Moisture %", 0, 100, 30, 1)
        crop = st.selectbox("Crop", ["Corn", "Cotton", "Soybean"])
        
        insect_img = st.file_uploader("Upload Insect Image (optional)",
                                     type=['jpg', 'jpeg', 'png'])
        if insect_img:
            st.image(insect_img, caption="Uploaded Insect Image")
            insect_img = image.load_img(insect_img, target_size=(224, 224))

        leaf_img = st.file_uploader("Upload Leaf Disease Image (optional)",
                                   type=['jpg', 'jpeg', 'png'])
        if leaf_img:
            st.image(leaf_img, caption="Uploaded Leaf Image")
            leaf_img = image.load_img(leaf_img, target_size=(224, 224))

        analyze_button = st.button("Analyze Farm Conditions")

    with status_col:
        st.header("Analysis Status & Results")
        display_area = st.empty()

        if analyze_button:
            try:
                with display_area.container():
                    status_area = st.empty()
                    progress_area = st.empty()

                    def update_status(message, progress, step):
                        if progress >= 0:
                            progress_value = min(max(progress, 0), 100) / 100.0
                            progress_area.progress(progress_value)
                            status_area.info(f"🔄 Step: {step}\n{message}")

                    insights = st.session_state.pf.get_insights(
                        soil_ph=soil_ph,
                        soil_moisture=soil_moisture,
                        latitude=latitude,
                        longitude=longitude,
                        area_acres=area,
                        crop=crop,
                        insect=insect_img,
                        leaf=leaf_img,
                        status_callback=update_status)

                    # Show completion animation
                    status_area.empty()
                    progress_area.empty()
                    show_completion_animation()

                    # Clear and show results
                    display_area.empty()
                    with display_area.container():
                        st.markdown("### 🌟 Farm Analysis Results")
                        st.markdown("---")
                        st.markdown(insights)

            except Exception as e:
                display_area.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    create_streamlit_app()