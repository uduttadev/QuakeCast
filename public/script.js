document.addEventListener('DOMContentLoaded', () => {
    // Initialize map centered on Alaska
    const map = L.map('map').setView([64.2008, -149.4937], 5);

    // Add a dark themed tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Store station markers to update them later
    const stationMarkers = {};

    // Fetch and display stations
    fetch('/api/stations')
        .then(response => response.json())
        .then(data => {
            if (data.message === 'success') {
                data.data.forEach(station => {
                    if (station.Latitude && station.Longitude) {
                        const marker = L.circleMarker([station.Latitude, station.Longitude], {
                            radius: 4,
                            fillColor: "#38bdf8",
                            color: "#fff",
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        })
                            .bindPopup(`<b>Station:</b> ${station.SiteName}<br>No prediction yet`)
                            .addTo(map);

                        stationMarkers[station.SiteName] = marker;
                    }
                });
            }
        })
        .catch(error => console.error('Error fetching stations:', error));

    const marker = L.marker([61.2181, -149.9003], { draggable: true }).addTo(map);

    // Update inputs when marker is dragged
    marker.on('dragend', function (event) {
        const position = marker.getLatLng();
        document.getElementById('latitude').value = position.lat.toFixed(4);
        document.getElementById('longitude').value = position.lng.toFixed(4);
    });

    // Update marker when map is clicked
    map.on('click', function (e) {
        marker.setLatLng(e.latlng);
        document.getElementById('latitude').value = e.latlng.lat.toFixed(4);
        document.getElementById('longitude').value = e.latlng.lng.toFixed(4);
    });

    // Update marker when inputs change
    const latInput = document.getElementById('latitude');
    const lngInput = document.getElementById('longitude');

    function updateMarkerFromInputs() {
        const lat = parseFloat(latInput.value);
        const lng = parseFloat(lngInput.value);
        if (!isNaN(lat) && !isNaN(lng)) {
            marker.setLatLng([lat, lng]);
            map.panTo([lat, lng]);
        }
    }

    latInput.addEventListener('change', updateMarkerFromInputs);
    lngInput.addEventListener('change', updateMarkerFromInputs);

    // Handle form submission
    const form = document.getElementById('predict-form');
    const resultContainer = document.getElementById('result-container');
    const predictionOutput = document.getElementById('prediction-output');
    const predictBtn = document.getElementById('predict-btn');
    const exportBtn = document.getElementById('export-btn');

    let lastPredictions = null;
    let lastParams = null;

    // Helper to get color based on PGA
    function getColor(pga) {
        return pga > 0.8 ? '#800026' :
            pga > 0.6 ? '#BD0026' :
                pga > 0.4 ? '#E31A1C' :
                    pga > 0.2 ? '#FC4E2A' :
                        pga > 0.1 ? '#FD8D3C' :
                            pga > 0.05 ? '#FEB24C' :
                                pga > 0.01 ? '#FED976' :
                                    '#FFEDA0';
    }

    exportBtn.addEventListener('click', () => {
        if (!lastPredictions || !lastParams) return;

        const { longitude, latitude, magnitude, depth } = lastParams;
        const filename = `${Math.round(longitude)}_${Math.round(latitude)}_${magnitude}_${depth}.csv`;

        // CSV Header
        let csvContent = "Site Name,Dist,PGA (%g),PGV (cm/s)\n";

        // CSV Rows
        lastPredictions.forEach(pred => {
            // Site Name | Dist | PGA (%g) | PGV (cm/s)
            const row = [
                pred.station,
                pred.distance.toFixed(4),
                pred.pga.toFixed(6),
                pred.pgv.toFixed(6)
            ].join(",");
            csvContent += row + "\n";
        });

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        if (link.download !== undefined) {
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const longitude = parseFloat(document.getElementById('longitude').value);
        const latitude = parseFloat(document.getElementById('latitude').value);
        const magnitude = parseFloat(document.getElementById('magnitude').value);
        const depth = parseFloat(document.getElementById('depth').value);

        predictBtn.disabled = true;
        predictBtn.innerHTML = '<span>Predicting...</span>';

        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ longitude, latitude, magnitude, depth })
            });

            if (!response.ok) {
                throw new Error('Prediction failed');
            }

            const data = await response.json();

            if (data.predictions) {
                lastPredictions = data.predictions;
                lastParams = { longitude, latitude, magnitude, depth };
                let maxPga = 0;

                data.predictions.forEach(pred => {
                    const stationName = pred.station;
                    const pga = pred.pga;
                    const pgv = pred.pgv;

                    if (pga > maxPga) maxPga = pga;

                    const marker = stationMarkers[stationName];
                    if (marker) {
                        marker.setStyle({
                            fillColor: getColor(pga),
                            radius: 6,
                            fillOpacity: 0.9
                        });
                        marker.setPopupContent(
                            `<b>Station:</b> ${stationName}<br>` +
                            `<b>Dist:</b> ${pred.distance.toFixed(1)} km<br>` +
                            `<b>PGA:</b> ${pga.toFixed(4)} g<br>` +
                            `<b>PGV:</b> ${pgv.toFixed(4)} cm/s`
                        );
                    }
                });

                predictionOutput.textContent = maxPga.toFixed(4);
                document.querySelector('.result-unit').textContent = 'Max PGA (g)';
                resultContainer.classList.remove('hidden');
            } else if (data.prediction) {
                // Fallback for single prediction
                predictionOutput.textContent = data.prediction.toFixed(4);
                resultContainer.classList.remove('hidden');
            }

        } catch (error) {
            console.error('Error:', error);
            alert('Failed to get prediction. Please try again.');
        } finally {
            predictBtn.disabled = false;
            predictBtn.innerHTML = '<span>Predict Intensity</span>';
        }
    });
});
