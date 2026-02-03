/**
 * MapToPoster - Web Widget (Embed Script)
 * 
 * Embeddable JavaScript widget for integrating MapToPoster
 * into any website.
 * 
 * Usage:
 * <div id="maptoposter-widget"></div>
 * <script src="https://cdn.maptoposter.com/widget.js"></script>
 * <script>
 *   MapToPosterWidget.init({
 *     container: '#maptoposter-widget',
 *     apiKey: 'your-api-key',
 *     apiUrl: 'https://api.maptoposter.com/api/v1'
 *   });
 * </script>
 */

(function(window) {
  'use strict';

  // Default configuration
  const DEFAULT_CONFIG = {
    apiUrl: 'http://localhost:8000/api/v1',
    apiKey: null,
    container: '#maptoposter-widget',
    theme: 'noir',
    enabledServices: ['geocoding', 'generator', 'themes', 'export'],
    defaultDistance: 8000,
    defaultPaperSize: 'A4'
  };

  // Widget state
  let config = {};
  let container = null;
  let currentPoster = null;

  /**
   * Initialize the widget
   */
  function init(userConfig) {
    config = { ...DEFAULT_CONFIG, ...userConfig };
    
    // Find container element
    container = typeof config.container === 'string'
      ? document.querySelector(config.container)
      : config.container;
    
    if (!container) {
      console.error('MapToPoster: Container not found');
      return;
    }

    // Render widget UI
    render();
    
    // Attach event listeners
    attachEventListeners();
    
    console.log('MapToPoster Widget initialized');
  }

  /**
   * Render widget UI
   */
  function render() {
    container.innerHTML = `
      <div class="mtp-widget" data-theme="${config.theme}">
        <div class="mtp-header">
          <h2>Create Your Map Poster</h2>
        </div>
        
        <div class="mtp-content">
          <!-- Location Input -->
          <div class="mtp-section">
            <label class="mtp-label">Location</label>
            <input 
              type="text" 
              id="mtp-address-input" 
              class="mtp-input" 
              placeholder="Enter city or address..."
            />
            <button id="mtp-geocode-btn" class="mtp-button mtp-button-primary">
              Find Location
            </button>
          </div>

          <!-- Coordinates Display -->
          <div id="mtp-coordinates" class="mtp-section" style="display:none;">
            <div class="mtp-info-box">
              <strong>Coordinates:</strong>
              <span id="mtp-coords-text"></span>
            </div>
          </div>

          <!-- Map Configuration -->
          <div id="mtp-config" class="mtp-section" style="display:none;">
            <label class="mtp-label">City Name</label>
            <input 
              type="text" 
              id="mtp-city-name" 
              class="mtp-input" 
              placeholder="e.g., Berlin"
            />

            <label class="mtp-label">Country (optional)</label>
            <input 
              type="text" 
              id="mtp-country-name" 
              class="mtp-input" 
              placeholder="e.g., Germany"
            />

            <label class="mtp-label">Zoom Level</label>
            <select id="mtp-distance" class="mtp-select">
              <option value="500">Neighborhood (500m)</option>
              <option value="2000">Village (2km)</option>
              <option value="8000" selected>City (8km)</option>
              <option value="15000">Metropolis (15km)</option>
            </select>

            <label class="mtp-label">Theme</label>
            <select id="mtp-theme" class="mtp-select">
              <option value="noir">Noir</option>
              <option value="blueprint">Blueprint</option>
              <option value="neon_cyberpunk">Neon Cyberpunk</option>
              <option value="japanese_ink">Japanese Ink</option>
              <option value="ocean">Ocean</option>
              <option value="sunset">Sunset</option>
            </select>

            <button id="mtp-generate-btn" class="mtp-button mtp-button-success">
              Generate Poster
            </button>
          </div>

          <!-- Loading State -->
          <div id="mtp-loading" class="mtp-loading" style="display:none;">
            <div class="mtp-spinner"></div>
            <p>Generating your poster...</p>
          </div>

          <!-- Result -->
          <div id="mtp-result" class="mtp-section" style="display:none;">
            <div class="mtp-success-box">
              ✓ Poster generated successfully!
            </div>
            <div id="mtp-poster-preview"></div>
            <button id="mtp-download-btn" class="mtp-button mtp-button-primary">
              Download Poster
            </button>
          </div>

          <!-- Error State -->
          <div id="mtp-error" class="mtp-error-box" style="display:none;">
            <strong>Error:</strong> <span id="mtp-error-text"></span>
          </div>
        </div>
      </div>
    `;

    // Inject styles
    injectStyles();
  }

  /**
   * Inject widget styles
   */
  function injectStyles() {
    if (document.getElementById('mtp-widget-styles')) return;

    const style = document.createElement('style');
    style.id = 'mtp-widget-styles';
    style.textContent = `
      .mtp-widget {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        max-width: 600px;
        margin: 0 auto;
        padding: 2rem;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
      }

      .mtp-header h2 {
        margin: 0 0 1.5rem 0;
        font-size: 1.75rem;
        color: #1a3a52;
      }

      .mtp-section {
        margin-bottom: 1.5rem;
      }

      .mtp-label {
        display: block;
        margin-bottom: 0.5rem;
        font-weight: 600;
        color: #2c2c2c;
      }

      .mtp-input, .mtp-select {
        width: 100%;
        padding: 0.75rem;
        border: 2px solid #e0e0e0;
        border-radius: 6px;
        font-size: 1rem;
        margin-bottom: 0.75rem;
        transition: border-color 0.2s;
      }

      .mtp-input:focus, .mtp-select:focus {
        outline: none;
        border-color: #1a3a52;
      }

      .mtp-button {
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 6px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
      }

      .mtp-button-primary {
        background: #1a3a52;
        color: white;
      }

      .mtp-button-primary:hover {
        background: #152e40;
        transform: translateY(-2px);
      }

      .mtp-button-success {
        background: #28a745;
        color: white;
        width: 100%;
      }

      .mtp-button-success:hover {
        background: #218838;
      }

      .mtp-info-box {
        padding: 1rem;
        background: #e3f2fd;
        border-radius: 6px;
        border-left: 4px solid #2196f3;
      }

      .mtp-success-box {
        padding: 1rem;
        background: #d4edda;
        border-radius: 6px;
        border-left: 4px solid #28a745;
        color: #155724;
        margin-bottom: 1rem;
      }

      .mtp-error-box {
        padding: 1rem;
        background: #f8d7da;
        border-radius: 6px;
        border-left: 4px solid #dc3545;
        color: #721c24;
      }

      .mtp-loading {
        text-align: center;
        padding: 2rem;
      }

      .mtp-spinner {
        width: 40px;
        height: 40px;
        margin: 0 auto 1rem auto;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #1a3a52;
        border-radius: 50%;
        animation: mtp-spin 1s linear infinite;
      }

      @keyframes mtp-spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `;

    document.head.appendChild(style);
  }

  /**
   * Attach event listeners
   */
  function attachEventListeners() {
    // Geocode button
    const geocodeBtn = document.getElementById('mtp-geocode-btn');
    geocodeBtn.addEventListener('click', handleGeocode);

    // Generate button
    const generateBtn = document.getElementById('mtp-generate-btn');
    generateBtn.addEventListener('click', handleGenerate);
  }

  /**
   * Handle geocoding
   */
 async function handleGeocode() {
    const address = document.getElementById('mtp-address-input').value;
    
    if (!address) {
      showError('Please enter an address');
      return;
    }

    hideError();
    setLoading(true);

    try {
      const response = await fetch(`${config.apiUrl}/geocode`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(config.apiKey && { 'Authorization': `Bearer ${config.apiKey}` })
        },
        body: JSON.stringify({ address })
      });

      if (!response.ok) {
        throw new Error('Geocoding failed');
      }

      const data = await response.json();
      
      // Store coordinates
      currentPoster = {
        latitude: data.latitude,
        longitude: data.longitude,
        formatted_address: data.formatted_address
      };

      // Show coordinates and config section
      document.getElementById('mtp-coords-text').textContent = 
        `${data.latitude.toFixed(4)}, ${data.longitude.toFixed(4)}`;
      document.getElementById('mtp-coordinates').style.display = 'block';
      document.getElementById('mtp-config').style.display = 'block';

      // Parse city name from address
      const cityMatch = address.match(/^([^,]+)/);
      if (cityMatch) {
        document.getElementById('mtp-city-name').value = cityMatch[1].trim();
      }

    } catch (error) {
      showError('Could not find location. Please try again.');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Handle poster generation
   */
  async function handleGenerate() {
    if (!currentPoster) {
      showError('Please geocode a location first');
      return;
    }

    const cityName = document.getElementById('mtp-city-name').value;
    const countryName = document.getElementById('mtp-country-name').value;
    const distance = parseInt(document.getElementById('mtp-distance').value);
    const theme = document.getElementById('mtp-theme').value;

    if (!cityName) {
      showError('Please enter a city name');
      return;
    }

    hideError();
    setLoading(true);

    try {
      const response = await fetch(`${config.apiUrl}/posters/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(config.apiKey && { 'Authorization': `Bearer ${config.apiKey}` })
        },
        body: JSON.stringify({
          latitude: currentPoster.latitude,
          longitude: currentPoster.longitude,
          city_name: cityName,
          country_name: countryName,
          theme: theme,
          distance: distance,
          paper_size: config.defaultPaperSize,
          dpi: 300
        })
      });

      if (!response.ok) {
        throw new Error('Poster generation failed');
      }

      const data = await response.json();
      
      // Show result
      document.getElementById('mtp-result').style.display = 'block';
      
      // Store poster ID for download
      currentPoster.poster_id = data.poster_id;

    } catch (error) {
      showError('Failed to generate poster. Please try again.');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  /**
   * Helper functions
   */
  function setLoading(loading) {
    const loadingEl = document.getElementById('mtp-loading');
    const configEl = document.getElementById('mtp-config');
    
    if (loading) {
      loadingEl.style.display = 'block';
      configEl.style.display = 'none';
    } else {
      loadingEl.style.display = 'none';
    }
  }

  function showError(message) {
    const errorEl = document.getElementById('mtp-error');
    document.getElementById('mtp-error-text').textContent = message;
    errorEl.style.display = 'block';
  }

  function hideError() {
    document.getElementById('mtp-error').style.display = 'none';
  }

  // Expose public API
  window.MapToPosterWidget = {
    init: init,
    version: '2.0.0'
  };

})(window);
