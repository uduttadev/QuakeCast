import streamlit as st
import folium
from streamlit_folium import st_folium

st.title("QuakeCast Anchorage Map") # name of the app
m = folium.Map(location=[61.2176, -149.8997], zoom_start=7) #location of anchorage

m.add_child(folium.LatLngPopup()) #click on map to get lat long

output = st_folium(m, width=700, height=500)

# Place sliders in the sidebar for a smaller, always-visible UI
# Slider for magnitude and depth
with st.sidebar:
    st.header("Earthquake Parameters")
    mag = st.slider("Magnitude", 1.0, 10.0, 5.0, 0.1)
    depth = st.slider("Depth (km)", 0, 700, 10, 1)