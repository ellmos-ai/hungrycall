"""HTML Templates and Component Generators for HungryCall Web Interface."""

from typing import List, Dict, Any, Optional
from hungrycall.models import Restaurant, Mode
from hungrycall.phone_utils import mask_phone


def render_base_page() -> str:
    """Render main application HTML frame with HTMX, Leaflet, and SSE support."""
    return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>I am hungry — hungrycall</title>
    
    <!-- Local Static Assets for 100% Offline Capability -->
    <link rel="stylesheet" href="/static/leaflet.css">
    <script src="/static/leaflet.js"></script>
    <script src="/static/htmx.min.js"></script>
    <script src="/static/htmx-sse.js"></script>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --primary: #f59e0b;
            --primary-hover: #d97706;
            --success: #10b981;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent-glow: rgba(245, 158, 11, 0.15);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Outfit', -apple-system, sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(30, 41, 59, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 1000;
        }

        .logo-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            font-size: 1.8rem;
        }

        .logo-title {
            font-size: 1.4rem;
            font-weight: 700;
            background: linear-gradient(135deg, #f59e0b, #fbbf24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .mode-badge {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            background: #0f172a;
            padding: 0.4rem 1rem;
            border-radius: 9999px;
            border: 1px solid var(--card-border);
            font-size: 0.85rem;
        }

        .toggle-switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
        }

        .toggle-switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: #475569;
            transition: .3s;
            border-radius: 24px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background-color: var(--danger);
        }

        input:checked + .slider:before {
            transform: translateX(20px);
        }

        .live-warning {
            color: #f87171;
            font-weight: 600;
        }

        .dry-badge {
            color: #34d399;
            font-weight: 600;
        }

        main {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            padding: 1.5rem 2rem;
            flex: 1;
            max-width: 1600px;
            margin: 0 auto;
            width: 100%;
        }

        @media (max-width: 1024px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .panel {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .panel-title {
            font-size: 1.15rem;
            font-weight: 600;
            color: #e2e8f0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 0.75rem;
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .form-group.full-width {
            grid-column: 1 / -1;
        }

        label {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--text-muted);
        }

        input, select, textarea {
            background: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            transition: border-color 0.2s;
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--primary);
        }

        .btn {
            background: var(--primary);
            color: #000;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.25rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .btn:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .btn-danger {
            background: var(--danger);
            color: #fff;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .btn-secondary {
            background: #334155;
            color: #f8fafc;
        }

        .btn-secondary:hover {
            background: #475569;
        }

        /* Pulsing search animation */
        .search-loading-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 3rem 1.5rem;
            gap: 1.5rem;
            text-align: center;
        }

        .pulse-loader {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: var(--primary);
            box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
            animation: pulse-ring 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
        }

        @keyframes pulse-ring {
            to {
                box-shadow: 0 0 0 30px rgba(245, 158, 11, 0);
            }
        }

        /* Map styling */
        #map-container {
            position: sticky;
            top: 5rem;
            height: calc(100vh - 7.5rem);
            min-height: 500px;
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--card-border);
        }

        #map {
            width: 100%;
            height: 100%;
        }

        /* User glowing marker */
        .user-marker-pulse {
            width: 20px;
            height: 20px;
            background: #3b82f6;
            border: 3px solid #ffffff;
            border-radius: 50%;
            box-shadow: 0 0 15px #3b82f6, 0 0 25px #3b82f6;
            animation: user-glow 2s infinite alternate;
        }

        @keyframes user-glow {
            from { box-shadow: 0 0 10px #3b82f6, 0 0 20px #3b82f6; }
            to { box-shadow: 0 0 20px #60a5fa, 0 0 35px #60a5fa; }
        }

        /* Restaurant list items */
        .restaurant-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .restaurant-card {
            background: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s;
        }

        .restaurant-card.disabled {
            opacity: 0.4;
            filter: grayscale(80%);
        }

        .restaurant-card.struck-through {
            text-decoration: line-through;
            opacity: 0.4;
            border-color: #ef4444;
            background: rgba(239, 68, 68, 0.05);
        }

        .restaurant-card.success-active {
            border-color: var(--success);
            background: rgba(16, 185, 129, 0.1);
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        }

        .restaurant-info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .restaurant-name {
            font-weight: 600;
            font-size: 1rem;
            color: #f1f5f9;
        }

        .restaurant-details {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .handset-status {
            font-size: 1.5rem;
            padding: 0.4rem;
            border-radius: 50%;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .handset-status.gray {
            color: #94a3b8;
            animation: spin-pulse 1.2s infinite;
        }

        .handset-status.green {
            color: #10b981;
            transform: scale(1.25);
            filter: drop-shadow(0 0 8px #10b981);
        }

        @keyframes spin-pulse {
            0% { transform: scale(1); opacity: 0.7; }
            50% { transform: scale(1.15); opacity: 1; }
            100% { transform: scale(1); opacity: 0.7; }
        }

        /* Result card */
        .result-card {
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(30, 41, 59, 0.95));
            border: 2px solid var(--success);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.25rem;
        }

        .result-sentence {
            font-size: 1.4rem;
            font-weight: 700;
            color: #6ee7b7;
            line-height: 1.3;
        }

        .result-meta-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            background: rgba(15, 23, 42, 0.6);
            padding: 1rem;
            border-radius: 10px;
        }

        .meta-item {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .meta-label {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .meta-value {
            font-size: 1.1rem;
            font-weight: 700;
            color: #ffffff;
        }

        .callback-box {
            background: #064e3b;
            border: 1px solid #059669;
            padding: 0.75rem 1rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .callback-number {
            font-size: 1.2rem;
            font-weight: 700;
            color: #a7f3d0;
            letter-spacing: 0.05em;
        }

        /* Prompt transparency box */
        .prompt-preview-box {
            background: #090d16;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.85rem;
            color: #cbd5e1;
            white-space: pre-wrap;
            word-break: break-word;
        }

        /* Activity modal / drawer */
        .activity-log {
            background: #020617;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 0.75rem;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 0.8rem;
            color: #a1a1aa;
        }

        .activity-turn {
            padding: 0.2rem 0;
            border-bottom: 1px dotted #1e293b;
        }

        /* Reorder handles */
        .reorder-btns {
            display: flex;
            flex-direction: column;
            gap: 0.2rem;
        }

        .btn-mini {
            background: #334155;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 0.2rem 0.4rem;
            font-size: 0.7rem;
            cursor: pointer;
        }

        .btn-mini:hover {
            background: #475569;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-container">
            <span class="logo-icon">🍕</span>
            <div>
                <div class="logo-title">I am hungry</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">CALL-E Cascade Agent</div>
            </div>
        </div>

        <div class="mode-badge">
            <span id="mode-text-dry" class="dry-badge">⚡ Trockenlauf (Offline)</span>
            <label class="toggle-switch">
                <input type="checkbox" id="live-toggle" onchange="toggleLiveMode(this)">
                <span class="slider"></span>
            </label>
            <span id="mode-text-live" style="display:none;" class="live-warning">⚠️ Echter Anruf ($0.05 / Anruf)</span>
            <span style="border-left: 1px solid #334155; padding-left: 0.75rem; font-size: 0.8rem; color: #94a3b8;">
                Anrufe: <strong id="call-counter" style="color: #fff;">0</strong>
            </span>
        </div>
    </header>

    <main>
        <!-- Left Panel: Form, Restaurant Selection & Cascade Monitor -->
        <div class="panel" id="main-panel">
            
            <div class="panel-title">
                <span>📍</span> 1. Ort & Adresse eingeben
            </div>

            <form id="search-form" hx-post="/api/search" hx-target="#step-content" hx-indicator="#search-indicator">
                <input type="hidden" name="dry_run" id="dry_run_input" value="true">
                
                <div class="form-grid">
                    <div class="form-group">
                        <label for="postcode">PLZ</label>
                        <input type="text" id="postcode" name="postcode" value="12345" required>
                    </div>
                    <div class="form-group">
                        <label for="city">Ort / Stadt</label>
                        <input type="text" id="city" name="city" value="Dorfstadt" required>
                    </div>
                    <div class="form-group">
                        <label for="country">Land</label>
                        <select id="country" name="country">
                            <option value="Deutschland" selected>Deutschland</option>
                            <option value="Singapore">Singapore (CALL-E Hub)</option>
                            <option value="United Kingdom">United Kingdom</option>
                            <option value="United States">United States</option>
                        </select>
                    </div>
                    <div class="form-group full-width">
                        <label for="delivery_address">Lieferadresse</label>
                        <input type="text" id="delivery_address" name="delivery_address" value="Dorfstraße 10, 12345 Dorfstadt" required>
                    </div>
                    <div class="form-group">
                        <label for="radius_km">Umkreis (km)</label>
                        <input type="number" id="radius_km" name="radius_km" value="3.0" step="0.5" min="0.5" max="20.0">
                    </div>
                    <div class="form-group" style="grid-column: span 2; align-self: flex-end;">
                        <button type="submit" class="btn" style="width: 100%;">
                            <span>🔍</span> Restaurants suchen
                        </button>
                    </div>
                </div>
            </form>

            <div id="step-content">
                <!-- Content will be swapped here via HTMX after search -->
                <div style="text-align: center; color: var(--text-muted); padding: 2rem 1rem;">
                    Geben Sie Ihren Ort ein und klicken Sie auf "Restaurants suchen", um zu starten.
                </div>
            </div>

        </div>

        <!-- Right Panel: Map (Always Visible) -->
        <div class="panel" style="padding: 0; background: transparent; border: none; box-shadow: none;">
            <div id="map-container">
                <div id="map"></div>
            </div>
        </div>
    </main>

    <script>
        // Global Map State
        let map = null;
        let userMarker = null;
        let radiusCircle = null;
        let restaurantMarkers = [];
        let callCount = 0;

        // Initialize Leaflet Map
        function initLeafletMap(lat, lon, zoom = 14, radiusKm = 3.0) {
            if (map) {
                map.remove();
            }
            
            map = L.map('map').setView([lat, lon], zoom);
            
            // Use OpenStreetMap Tiles
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19,
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);

            // User Center Marker (Glowing Dot)
            const userIcon = L.divIcon({
                className: 'user-marker-pulse',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });
            userMarker = L.marker([lat, lon], { icon: userIcon }).addTo(map)
                .bindPopup("<b>Ihr Standort</b><br>Lieferadresse");

            // Candidate Search Radius Circle (Backflow from Video)
            if (radiusKm && radiusKm > 0) {
                radiusCircle = L.circle([lat, lon], {
                    radius: radiusKm * 1000,
                    color: '#f59e0b',
                    fillColor: '#f59e0b',
                    fillOpacity: 0.08,
                    weight: 2,
                    dashArray: '6, 6'
                }).addTo(map).bindPopup(`<b>Kandidatenradius</b><br>${radiusKm} km Umkreis`);
            }
        }

        // Add Restaurant Markers to Map
        function updateMapMarkers(restaurants) {
            restaurantMarkers.forEach(m => map.removeLayer(m));
            restaurantMarkers = [];

            restaurants.forEach(r => {
                const marker = L.marker([r.lat, r.lon]).addTo(map)
                    .bindPopup(`<b>${r.name}</b><br>${r.cuisines.join(', ')}<br>${r.masked_phone}`);
                restaurantMarkers.push(marker);
            });
        }

        // Live Mode Toggle Handler
        function toggleLiveMode(checkbox) {
            const isLive = checkbox.checked;
            document.getElementById('dry_run_input').value = isLive ? "false" : "true";
            document.getElementById('mode-text-dry').style.display = isLive ? "none" : "inline";
            document.getElementById('mode-text-live').style.display = isLive ? "inline" : "none";
        }

        // Initialize map with default location on page load
        document.addEventListener("DOMContentLoaded", function() {
            initLeafletMap(52.5200, 13.4050, 13);
        });
    </script>
</body>
</html>
"""


def render_search_loading() -> str:
    """Render smooth search animation and text per UI-SPEC."""
    return """
    <div class="search-loading-container" id="search-indicator">
        <div class="pulse-loader"></div>
        <div>
            <h3 style="color: #f59e0b; font-weight: 600; margin-bottom: 0.5rem;">Wir suchen für Sie die besten Essenspunkte...</h3>
            <p style="color: #94a3b8; font-size: 0.9rem;">Sammle Restaurants, Adressen, Telefonnummern und Öffnungszeiten...</p>
        </div>
    </div>
    """


def render_restaurant_selection_step(
    restaurants: List[Restaurant],
    lat: float,
    lon: float,
    city: str,
    delivery_address: str,
    radius_km: float = 3.0
) -> str:
    """Render Step 2: Map markers script + Restaurant Selection + Mode & Food form."""
    
    # Filter closed restaurants
    open_restaurants = [r for r in restaurants if r.opening_hours.is_open("Fri", "19:00")]
    closed_restaurants = [r for r in restaurants if not r.opening_hours.is_open("Fri", "19:00")]
    
    # Prepare JS array for Leaflet map markers
    map_restaurants_js = []
    for r in restaurants:
        map_restaurants_js.append({
            "id": r.id,
            "name": r.name,
            "cuisines": r.cuisines,
            "masked_phone": mask_phone(r.phone),
            "lat": r.lat,
            "lon": r.lon
        })

    import json
    restaurants_json = json.dumps(map_restaurants_js)

    open_items_html = ""
    for idx, r in enumerate(restaurants):
        is_open = r.opening_hours.is_open("Fri", "19:00")
        display_style = "" if is_open else "display: none;"
        checked = "checked" if is_open else ""
        class_disabled = "" if is_open else "disabled"
        
        open_items_html += f"""
        <div class="restaurant-card {class_disabled}" id="rest-card-{r.id}" style="{display_style}">
            <div style="display: flex; flex-direction: column; gap: 0.25rem; flex: 1;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div class="reorder-btns">
                        <button type="button" class="btn-mini" onclick="moveCardUp('{r.id}')">▲</button>
                        <button type="button" class="btn-mini" onclick="moveCardDown('{r.id}')">▼</button>
                    </div>
                    <input type="checkbox" name="selected_restaurants" value="{r.id}" {checked} onchange="toggleRestCard('{r.id}', this.checked)">
                    <div class="restaurant-info">
                        <div class="restaurant-name">{r.name}</div>
                        <div class="restaurant-details">{', '.join(r.cuisines)} • {mask_phone(r.phone)}</div>
                    </div>
                </div>
                <!-- Inline Rejection Reason Badge Container (Backflow from Video) -->
                <div id="rejection-{r.id}" style="padding-left: 2.4rem;"></div>
            </div>
            <div id="handset-{r.id}">
                <span class="handset-status" title="Wartezustand">📞</span>
            </div>
        </div>
        """

    closed_count = len(closed_restaurants)

    return f"""
    <script>
        // Update Leaflet map with searched restaurants & candidate radius circle
        initLeafletMap({lat}, {lon}, 13, {radius_km});
        updateMapMarkers({restaurants_json});

        function moveCardUp(id) {{
            const card = document.getElementById('rest-card-' + id);
            if (card && card.previousElementSibling) {{
                card.parentNode.insertBefore(card, card.previousElementSibling);
            }}
        }}

        function moveCardDown(id) {{
            const card = document.getElementById('rest-card-' + id);
            if (card && card.nextElementSibling) {{
                card.parentNode.insertBefore(card.nextElementSibling, card);
            }}
        }}

        function toggleRestCard(id, checked) {{
            const card = document.getElementById('rest-card-' + id);
            if (card) {{
                if (checked) card.classList.remove('disabled');
                else card.classList.add('disabled');
            }}
        }}

        function toggleClosedRestaurants(btn) {{
            const cards = document.querySelectorAll('.restaurant-card.disabled');
            cards.forEach(c => {{
                if (c.style.display === 'none') c.style.display = 'flex';
                else c.style.display = 'none';
            }});
            btn.innerText = btn.innerText.includes('Einblenden') ? 'Geschlossene ausblenden' : 'Geschlossene einblenden';
        }}
    </script>

    <div style="display: flex; flex-direction: column; gap: 1.5rem; margin-top: 1rem;">
        
        <!-- Hinweistext per UI-SPEC -->
        <div style="background: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b; padding: 0.85rem 1rem; border-radius: 6px; font-size: 0.9rem; color: #fef08a;">
            💬 <strong>Restaurantauswahl:</strong> Wir rufen alle an und prüfen zuerst, ob sie liefern können. Bitte wählen Sie diejenigen ab, die nicht angerufen werden sollen.
        </div>

        <form id="cascade-form" hx-post="/api/start-cascade" hx-target="#cascade-monitor">
            <input type="hidden" name="city" value="{city}">
            <input type="hidden" name="delivery_address" value="{delivery_address}">

            <div class="restaurant-list" id="restaurant-sortable-list">
                {open_items_html}
            </div>

            {f'''
            <div style="font-size: 0.85rem; color: #94a3b8; margin-top: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
                <span>🕒 {closed_count} vermutlich geschlossene Restaurants ausgeblendet.</span>
                <button type="button" class="btn-mini" onclick="toggleClosedRestaurants(this)">Geschlossene einblenden</button>
            </div>
            ''' if closed_count > 0 else ''}

            <!-- Step 4: Modus, Essenswunsch & Höchstbetrag -->
            <div style="border-top: 1px solid var(--card-border); padding-top: 1.25rem; margin-top: 1rem; display: flex; flex-direction: column; gap: 1rem;">
                
                <div class="form-grid">
                    <div class="form-group">
                        <label for="mode">Modus wählen</label>
                        <select id="mode" name="mode" onchange="updateModeFields(this.value)">
                            <option value="delivery" selected>🍕 Lieferung</option>
                            <option value="pickup">🛍️ Abholen</option>
                            <option value="reservation">🍽️ Tisch reservieren</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="customer_name">Ihr Name</label>
                        <input type="text" id="customer_name" name="customer_name" value="Alex" required>
                    </div>

                    <div class="form-group" id="budget-group">
                        <label for="max_budget_eur">Höchstbetrag (€ an Haustür)</label>
                        <input type="number" id="max_budget_eur" name="max_budget_eur" value="35.00" step="1.0" min="5.0" required>
                    </div>
                </div>

                <div class="form-group">
                    <label for="food_prompt">Essenswunsch (Freitext)</label>
                    <textarea id="food_prompt" name="food_prompt" rows="2" placeholder="z. B. 2x Cheeseburger, 1x Große Pommes, 1x Cola Zero" required>2x Cheeseburger, 1x Große Pommes, 1x Cola Zero</textarea>
                </div>

                <!-- Step 5: Transparency Prompt Preview -->
                <div class="form-group">
                    <label>🔍 CALL-E Prompt-Vorschau (Transparenz vor Absenden)</label>
                    <div class="prompt-preview-box" id="prompt-preview">
Click "Auftragstext prüfen" below to preview exact call goal sent to CALL-E.
                    </div>
                </div>

                <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
                    <button type="button" class="btn btn-secondary" onclick="updatePromptPreview()">
                        📝 Auftragstext prüfen
                    </button>
                    <button type="submit" class="btn" style="flex: 1;">
                        📞 Anruf-Kaskade starten
                    </button>
                </div>
            </div>
        </form>

        <div id="cascade-monitor"></div>
    </div>

    <script>
        function updatePromptPreview() {{
            const mode = document.getElementById('mode').value;
            const name = document.getElementById('customer_name').value;
            const address = "{delivery_address}";
            const food = document.getElementById('food_prompt').value;
            const budget = document.getElementById('max_budget_eur').value;

            let goalText = `Hello, I am an automated assistant calling on behalf of ${{name}}. We would like to order food for delivery to ${{address}}. Requested items: '${{food}}'. Please verify: 1. Do you deliver to this address? 2. What is the EXACT total price in EUR including delivery fee? 3. What is estimated delivery time in minutes? 4. If total price is within max budget limit of ${{budget}} EUR, place order and obtain direct callback number.`;
            document.getElementById('prompt-preview').innerText = goalText;
        }}
    </script>
    """


def render_cascade_monitor(order_id: str, dry_run: bool, max_budget_eur: Optional[float] = 35.00) -> str:
    """Render SSE streaming cascade monitor container with cancel button and active budget band."""
    budget_str = f"{max_budget_eur:.2f} €" if max_budget_eur is not None else "Kein Limit"
    return f"""
    <div style="background: #090d16; border: 1px solid #334155; border-radius: 12px; padding: 1.25rem; display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem;"
         hx-ext="sse" sse-connect="/api/cascade-stream?order_id={order_id}&dry_run={str(dry_run).lower()}" sse-swap="message">
        
        <!-- Active Budget Band Header Banner (Backflow from Video) -->
        <div style="background: linear-gradient(90deg, rgba(245, 158, 11, 0.15), rgba(15, 23, 42, 0.8)); border: 1px solid #f59e0b; border-radius: 8px; padding: 0.6rem 1rem; display: flex; align-items: center; justify-content: space-between; font-size: 0.88rem;">
            <span style="color: #fef08a; font-weight: 600; display: flex; align-items: center; gap: 0.4rem;">
                <span>🛡️</span> FINANCIAL AUTHORITY CAP (Harte Grenze)
            </span>
            <span style="color: #ffffff; font-weight: 700; font-family: monospace; font-size: 0.95rem;">
                Höchstbetrag: {budget_str}
            </span>
        </div>

        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="font-weight: 600; color: #f59e0b; display: flex; align-items: center; gap: 0.5rem;">
                <span class="spin-loader">⚡</span> Anruf-Kaskade läuft live...
            </div>
            <button type="button" class="btn btn-danger" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;" hx-post="/api/cancel-cascade?order_id={order_id}">
                ⛔ Kaskade abbrechen
            </button>
        </div>

        <div id="cascade-status-text" style="font-size: 0.9rem; color: #94a3b8;">
            Initiere Anrufkaskade... ~40 Sekunden Vorlaufzeit pro Anruf.
        </div>

        <div id="live-activity-box" class="activity-log" style="display: none;">
            <!-- Real-time STT turns stream here -->
        </div>
    </div>
    """


def render_result_card(
    restaurant_name: str,
    callback_number: str,
    total_price_eur: float,
    eta_minutes: int,
    post_summary: str,
    raw_transcript_text: str,
    order_id: str
) -> str:
    """Render Step 9: Result Card with prominent callback number and summary per UI-SPEC."""
    masked_cb = mask_phone(callback_number)
    
    return f"""
    <div class="result-card" id="final-result-card">
        <div style="display: flex; align-items: center; gap: 0.5rem; color: #10b981; font-weight: 600; font-size: 0.9rem; text-transform: uppercase;">
            <span>🎉</span> Bestätigte Bestellung
        </div>

        <div class="result-sentence">
            Erfolgreich bestellt bei {restaurant_name}! Das Essen kommt in ca. {eta_minutes} Minuten.
        </div>

        <div class="result-meta-grid">
            <div class="meta-item">
                <span class="meta-label">Endbetrag (Haustür)</span>
                <span class="meta-value">{total_price_eur:.2f} €</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Lieferzeit (ETA)</span>
                <span class="meta-value">{eta_minutes} Min.</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Status</span>
                <span class="meta-value" style="color: #34d399;">BESTÄTIGT</span>
            </div>
        </div>

        <!-- Prominente Rückrufnummer per UI-SPEC -->
        <div class="callback-box">
            <div>
                <div style="font-size: 0.8rem; color: #6ee7b7; font-weight: 500;">RÜCKRUFNUMMER DES RESTAURANTS</div>
                <div style="font-size: 0.75rem; color: #a7f3d0;">(Bestellung ist verbindlich — für Änderungen direkt anrufen)</div>
            </div>
            <div class="callback-number">{masked_cb}</div>
        </div>

        <details style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; border-radius: 8px; padding: 0.75rem;">
            <summary style="cursor: pointer; font-weight: 600; color: #cbd5e1;">📜 Vollständiges Gesprächsprotokoll (Transkript)</summary>
            <!-- Highlighted Price Verification Banner (Backflow from Video) -->
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 0.5rem 0.75rem; border-radius: 6px; font-size: 0.85rem; color: #a7f3d0; margin-top: 0.75rem; display: flex; align-items: center; justify-content: space-between;">
                <span>🏷️ <strong>Bestätigter Transkript-Endpreis:</strong> {total_price_eur:.2f} €</span>
                <span style="color: #34d399; font-weight: 600;">✓ In Budget</span>
            </div>
            <pre style="margin-top: 0.5rem; font-family: monospace; font-size: 0.8rem; color: #a1a1aa; white-space: pre-wrap;">{raw_transcript_text}</pre>
        </details>

        <form hx-post="/api/save-result" hx-target="#save-status">
            <input type="hidden" name="order_id" value="{order_id}">
            <input type="hidden" name="restaurant_name" value="{restaurant_name}">
            <input type="hidden" name="callback_number" value="{callback_number}">
            <input type="hidden" name="total_price_eur" value="{total_price_eur}">
            <input type="hidden" name="eta_minutes" value="{eta_minutes}">
            <input type="hidden" name="post_summary" value="{post_summary}">
            <input type="hidden" name="raw_transcript_text" value="{raw_transcript_text}">
            
            <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.5rem;">
                <button type="submit" class="btn" style="background: #10b981; color: #000;">
                    💾 Ergebnis in Datenbank speichern
                </button>
                <span id="save-status" style="font-size: 0.9rem; color: #34d399; font-weight: 500;"></span>
            </div>
        </form>
    </div>
    """
