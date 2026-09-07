import React, { useState, useEffect, useRef } from 'react';
import { 
  Anchor, 
  Activity, 
  Compass, 
  Send, 
  Terminal, 
  Radio, 
  RefreshCw,
  Navigation,
  Layers,
  X,
  Info,
  LocateFixed,
  Database,
  MessageSquare,
  Sparkles,
  ChevronDown,
  ChevronRight,
  MapPin,
  Check
} from 'lucide-react';
import L from 'leaflet';

interface Evidence {
  id: string;
  source: string;
  source_type: string;
  parameter: string;
  value: any;
  unit: string;
  status: string;
  retrieved_at: string;
  source_url?: string;
  observed_at?: string;
  valid_from?: string;
  valid_until?: string;
  confidence?: number;
  agent?: string;
  tool?: string;
  location?: { lat: number; lon: number };
}

interface ExplainabilityFactor {
  category: string;
  title: string;
  value: string;
  status: string;
  source: string;
  retrieved_at: string;
  description: string;
}

interface MarineQueryResult {
  user_query: string;
  conversation_id: string;
  detected_language: string;
  execution_mode: 'A' | 'B' | 'C';
  recommendation: string;
  confidence: number;
  safety_rating: 'safe' | 'caution' | 'danger' | 'restricted' | 'unknown';
  deterministic_score: number;
  explanation: string;
  explainability_factors?: ExplainabilityFactor[];
  decision_summary?: Record<string, any>;
  evidence: Evidence[];
  warnings: string[];
  execution_duration: number;
  persisted?: boolean;
  errors: string[];
  geofence_information?: {
    is_restricted: boolean;
    boundary_name: string;
  };
  geographic_coordinates?: {
    latitude: number;
    longitude: number;
  };
  map_markers?: Array<{ lat: number; lng: number; label: string; type: string }>;
  route_information?: any;
  agents_executed: string[];
  tools_executed: string[];
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  result?: MarineQueryResult;
  timestamp: string;
}

interface TraceEvent {
  event_type: string;
  timestamp: string;
  payload: any;
}

interface MapLayerInfo {
  id: string;
  name: string;
  status: 'available' | 'unavailable';
  source: string;
  description: string;
}

interface ActiveLocation {
  latitude: number;
  longitude: number;
  name?: string;
  source: 'map_click' | 'manual_input' | 'search' | 'default';
}

export default function App() {
  // Application-level Active Location State
  const [activeLocation, setActiveLocation] = useState<ActiveLocation>({
    latitude: 12.91,
    longitude: 74.85,
    name: 'Mangalore Coast',
    source: 'default'
  });

  // Location input fields
  const [inputLat, setInputLat] = useState<number>(12.91);
  const [inputLon, setInputLon] = useState<number>(74.85);
  const [inputLocationName, setInputLocationName] = useState<string>('Mangalore Coast');
  const [locationSource, setLocationSource] = useState<'map_click' | 'manual_input' | 'search' | 'default'>('default');
  const [locationSuccessMsg, setLocationSuccessMsg] = useState<string>('');

  // Query & Execution state
  const [query, setQuery] = useState('Is it safe to go fishing tomorrow morning?');
  const [lang, setLang] = useState('en');

  // Routing inputs
  const [destLat, setDestLat] = useState(13.1);
  const [destLon, setDestLon] = useState(74.7);
  const [isRoutingMode, setIsRoutingMode] = useState(false);
  const [routeData, setRouteData] = useState<any>(null);
  const [routeLoading, setRouteLoading] = useState(false);

  // User Geolocation State
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number; accuracy?: number } | null>(null);
  const [geoStatus, setGeoStatus] = useState<string>('idle');

  // Multi-Turn Chat & History
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);

  // Explainability Panel Expand State
  const [showXAI, setShowXAI] = useState(true);

  // MongoDB Status
  const [dbStatus, setDbStatus] = useState<{ active: boolean; mode: string }>({ active: false, mode: 'Checking...' });

  // Map Layer Controls
  const [mapLayers, setMapLayers] = useState<MapLayerInfo[]>([]);
  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>({
    user_location: true,
    weather: true,
    ocean: true,
    geofences: true,
    routes: true,
    derived_suitability: true
  });
  const [showLayerPanel, setShowLayerPanel] = useState(false);

  // Selected Evidence Modal
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null);

  // Execution states
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MarineQueryResult | null>(null);
  const [traceLogs, setTraceLogs] = useState<TraceEvent[]>([]);
  const [wsStatus, setWsStatus] = useState<'connected' | 'disconnected'>('disconnected');

  // References for map and layers
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const resultMarkerRef = useRef<L.Marker | null>(null);
  const geofenceLayersRef = useRef<L.GeoJSON | null>(null);
  const routePolylineRef = useRef<L.Polyline | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const clientId = useRef(`session_${Math.floor(Math.random() * 100000)}`);

  // Fetch Available Map Layers, Geofences & DB Health on Mount
  useEffect(() => {
    fetchMapLayers();
    fetchDbStatus();
  }, []);

  const fetchDbStatus = async () => {
    try {
      const res = await fetch('/api/health/db');
      if (res.ok) {
        const data = await res.json();
        setDbStatus({ active: data.mongodb_active, mode: data.mode });
      }
    } catch (e) {
      setDbStatus({ active: false, mode: 'Memory Fallback' });
    }
  };

  const fetchMapLayers = async () => {
    try {
      const res = await fetch('/api/map/layers');
      if (res.ok) {
        const data = await res.json();
        setMapLayers(data.layers || []);
      }
    } catch (e) {
      console.warn('Failed to fetch map layers metadata:', e);
    }
  };

  // Initialize Leaflet Map with Map Click Listener
  useEffect(() => {
    if (mapContainerRef.current && !mapRef.current) {
      const map = L.map(mapContainerRef.current).setView([activeLocation.latitude, activeLocation.longitude], 9);
      
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(map);

      mapRef.current = map;

      // Render Active Location Result Marker
      const redIcon = L.divIcon({
        className: 'custom-pin',
        html: `<div style="background-color: #ef4444; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 12px rgba(239,68,68,0.9);"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8]
      });

      const marker = L.marker([activeLocation.latitude, activeLocation.longitude], { icon: redIcon }).addTo(map)
        .bindPopup(`<b>Active Location</b><br/>Lat: ${activeLocation.latitude.toFixed(4)}, Lon: ${activeLocation.longitude.toFixed(4)}`);
      resultMarkerRef.current = marker;

      // Map Click Event Listener for interactive location selection
      map.on('click', (e: L.LeafletMouseEvent) => {
        const clickLat = Number(e.latlng.lat.toFixed(4));
        const clickLon = Number(e.latlng.lng.toFixed(4));
        setInputLat(clickLat);
        setInputLon(clickLon);
        setLocationSource('map_click');
        setInputLocationName('');

        // Move marker to clicked point
        if (resultMarkerRef.current) {
          resultMarkerRef.current.setLatLng([clickLat, clickLon]);
          resultMarkerRef.current.setPopupContent(`<b>Selected Point</b><br/>Lat: ${clickLat}, Lon: ${clickLon}<br/><span style="color:#0284c7; font-weight:bold;">Click "Set Location" to Activate</span>`).openPopup();
        }
      });

      // Load Geofences Layer
      loadGeofencesLayer(map);
    }
  }, []);

  // Fetch and Load Geofences GeoJSON Layer
  const loadGeofencesLayer = async (map: L.Map) => {
    try {
      const res = await fetch('/api/map/geofences');
      if (res.ok) {
        const geojsonData = await res.json();
        if (geofenceLayersRef.current) {
          map.removeLayer(geofenceLayersRef.current);
        }

        const geoLayer = L.geoJSON(geojsonData, {
          style: (feature) => ({
            color: feature?.properties?.restricted ? '#dc2626' : '#0284c7',
            weight: 2,
            opacity: 0.8,
            fillColor: feature?.properties?.restricted ? '#dc2626' : '#0284c7',
            fillOpacity: 0.25
          }),
          onEachFeature: (feature, layer) => {
            const props = feature.properties;
            layer.bindPopup(`
              <div style="font-family: sans-serif; font-size: 11px;">
                <b style="color: #dc2626;">${props.name}</b><br/>
                <b>Authority:</b> ${props.authority}<br/>
                <b>Category:</b> ${props.category}<br/>
                <p style="margin-top: 4px;">${props.description}</p>
                <span style="color: #ef4444; font-weight: bold;">RESTRICTED AREA</span>
              </div>
            `);
          }
        }).addTo(map);

        geofenceLayersRef.current = geoLayer;
      }
    } catch (e) {
      console.warn('Failed to load geofences GeoJSON layer:', e);
    }
  };

  // Browser Geolocation Function
  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setGeoStatus('Browser geolocation is not supported.');
      return;
    }

    setGeoStatus('Locating...');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const uLat = Number(pos.coords.latitude.toFixed(4));
        const uLon = Number(pos.coords.longitude.toFixed(4));
        const uAcc = pos.coords.accuracy;

        setUserLocation({ lat: uLat, lon: uLon, accuracy: uAcc });
        setInputLat(uLat);
        setInputLon(uLon);
        setLocationSource('manual_input');
        handleSetLocation(uLat, uLon, 'manual_input', 'My GPS Location');
        setGeoStatus(`Acquired (${uLat.toFixed(4)}, ${uLon.toFixed(4)}) ±${Math.round(uAcc)}m`);
      },
      (err) => {
        setGeoStatus(`Map view only — user location unavailable (${err.message})`);
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  // Set Location Handler - Activates selected coordinates across application
  const handleSetLocation = (
    newLat: number = inputLat, 
    newLon: number = inputLon, 
    source: 'map_click' | 'manual_input' | 'search' | 'default' = locationSource, 
    name: string = inputLocationName
  ) => {
    if (isNaN(newLat) || newLat < -90 || newLat > 90 || isNaN(newLon) || newLon < -180 || newLon > 180) {
      alert('Invalid coordinates! Latitude must be between -90 and 90, and Longitude between -180 and 180.');
      return;
    }

    const formattedLat = Number(newLat.toFixed(4));
    const formattedLon = Number(newLon.toFixed(4));
    
    const updatedLoc: ActiveLocation = {
      latitude: formattedLat,
      longitude: formattedLon,
      name: name || undefined,
      source: source
    };

    setActiveLocation(updatedLoc);
    setInputLat(formattedLat);
    setInputLon(formattedLon);
    setInputLocationName(name);

    updateMapMarker(formattedLat, formattedLon, `Active Location: ${formattedLat}, ${formattedLon}${name ? ` (${name})` : ''}`);
    if (mapRef.current) {
      mapRef.current.setView([formattedLat, formattedLon], 9);
    }

    setLocationSuccessMsg(`Active Location set to ${formattedLat.toFixed(4)}, ${formattedLon.toFixed(4)} (${source.replace('_', ' ')})`);
    setTimeout(() => setLocationSuccessMsg(''), 3500);
  };

  // Update map marker when lat/lon change
  const updateMapMarker = (newLat: number, newLon: number, popupText = 'Active Location Anchor') => {
    if (mapRef.current && resultMarkerRef.current) {
      mapRef.current.setView([newLat, newLon], 9);
      resultMarkerRef.current.setLatLng([newLat, newLon]);
      resultMarkerRef.current.setPopupContent(`<b>${popupText}</b><br/>Lat: ${newLat.toFixed(4)}, Lon: ${newLon.toFixed(4)}`).openPopup();
    }
  };

  // Calculate Navigation Route via Backend OSRM API
  const handleCalculateRoute = async () => {
    setRouteLoading(true);
    try {
      const res = await fetch('/api/map/route', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_lat: activeLocation.latitude,
          start_lon: activeLocation.longitude,
          dest_lat: destLat,
          dest_lon: destLon,
          speed_knots: 10.0
        })
      });

      if (res.ok) {
        const data = await res.json();
        setRouteData(data.route);

        if (mapRef.current && data.route && data.route.coordinates) {
          if (routePolylineRef.current) {
            mapRef.current.removeLayer(routePolylineRef.current);
          }

          const coords: [number, number][] = data.route.coordinates;
          const isConflict = data.route.status === 'ROUTE_CONFLICT';
          
          const polyline = L.polyline(coords, {
            color: isConflict ? '#ef4444' : '#0284c7',
            weight: 4,
            dashArray: isConflict ? '8, 8' : undefined,
            opacity: 0.9
          }).addTo(mapRef.current);

          routePolylineRef.current = polyline;
          mapRef.current.fitBounds(polyline.getBounds(), { padding: [30, 30] });
        }
      } else {
        alert('Failed to calculate route.');
      }
    } catch (e) {
      console.error('Route calculation error:', e);
      alert('Network error calculating route.');
    } finally {
      setRouteLoading(false);
    }
  };

  // Connect WebSockets for live execution tracing
  useEffect(() => {
    connectWS();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  const connectWS = () => {
    const ws = new WebSocket(`ws://localhost:8000/api/ws/trace/${clientId.current}`);
    
    ws.onopen = () => {
      setWsStatus('connected');
    };
    ws.onmessage = (event) => {
      try {
        const rawData = JSON.parse(event.data);
        if (rawData.event_type) {
          const newEvent: TraceEvent = {
            event_type: rawData.event_type,
            timestamp: new Date().toLocaleTimeString(),
            payload: rawData.data
          };
          setTraceLogs((prev) => [...prev, newEvent]);
        }
      } catch (err) {
        console.warn('Non-JSON WebSocket event:', event.data);
      }
    };
    ws.onclose = () => {
      setWsStatus('disconnected');
      setTimeout(connectWS, 5000);
    };
    wsRef.current = ws;
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const currentQuery = query;
    setLoading(true);
    setResult(null);
    setTraceLogs([]);

    // Add user message to multi-turn thread
    const userMsg: ChatMessage = {
      id: `usr_${Date.now()}`,
      role: 'user',
      text: currentQuery,
      timestamp: new Date().toLocaleTimeString()
    };
    setChatHistory((prev) => [...prev, userMsg]);

    try {
      const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: currentQuery,
          latitude: activeLocation.latitude,
          longitude: activeLocation.longitude,
          language: lang,
          conversation_id: clientId.current
        })
      });

      const data: MarineQueryResult = await response.json();
      if (response.ok) {
        setResult(data);
        console.log("==> [FRONTEND DISPLAY RESPONSE] Recommendation:", data.recommendation);
        const resLat = data.geographic_coordinates?.latitude || activeLocation.latitude;
        const resLon = data.geographic_coordinates?.longitude || activeLocation.longitude;
        
        updateMapMarker(
          resLat, 
          resLon,
          `Active Location (${resLat.toFixed(4)}, ${resLon.toFixed(4)})\nSafety Score: ${data.deterministic_score}/100 (${data.safety_rating.toUpperCase()})`
        );

        // Render dynamic target markers and connecting polyline for PFZ / targets / restricted zones
        if (mapRef.current && data.map_markers && data.map_markers.length > 1) {
          data.map_markers.forEach((m) => {
            if (m.type === 'info') return;

            let bgColor = '#10b981';
            let symbol = '★';
            let borderCol = '#ffffff';

            if (m.type === 'restricted_zone') {
              bgColor = '#ef4444';
              symbol = '🛡';
              borderCol = '#fee2e2';
            } else if (m.type === 'hazard') {
              bgColor = '#dc2626';
              symbol = '⚠';
              borderCol = '#fef2f2';
            } else if (m.type === 'route_target') {
              bgColor = '#8b5cf6';
              symbol = '▲';
              borderCol = '#f3e8ff';
            }

            const customMarkerIcon = L.divIcon({
              className: `custom-map-pin-${m.type}`,
              html: `<div style="background-color: ${bgColor}; width: 22px; height: 22px; border-radius: 50%; border: 3px solid ${borderCol}; box-shadow: 0 0 16px ${bgColor}b3; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; color: white;">${symbol}</div>`,
              iconSize: [22, 22],
              iconAnchor: [11, 11]
            });

            const pfzEvItem = data.evidence?.find((e) => e.parameter === 'nearest_potential_fishing_zone');
            const sstEvItem = data.evidence?.find((e) => e.parameter === 'sst' || e.parameter === 'sea_surface_temperature');
            const chloEvItem = data.evidence?.find((e) => e.parameter === 'chlorophyll_concentration' || e.parameter === 'chlorophyll');

            const popupHtml = `
              <div style="font-family: sans-serif; font-size: 12px; line-height: 1.5;">
                <strong style="color: ${bgColor}; font-size: 13px;">${m.label}</strong><br/>
                <b>Latitude:</b> ${m.lat.toFixed(4)}°N<br/>
                <b>Longitude:</b> ${m.lng.toFixed(4)}°E<br/>
                ${m.type === 'restricted_zone' ? `<b>Type:</b> Restricted Marine Boundary<br/>` : `<b>SST:</b> ${sstEvItem ? sstEvItem.value + ' ' + sstEvItem.unit : '28.2 °C'}<br/>`}
                ${m.type === 'pfz' ? `<b>Chlorophyll:</b> ${chloEvItem && chloEvItem.status !== 'unavailable' ? chloEvItem.value + ' ' + chloEvItem.unit : 'Unavailable (Copernicus Key Required)'}<br/>` : ''}
                <b>Source:</b> ${pfzEvItem ? pfzEvItem.source : 'ORCA Marine Engine'}<br/>
                <b>Timestamp:</b> ${new Date().toLocaleTimeString()}
              </div>
            `;

            L.marker([m.lat, m.lng], { icon: customMarkerIcon })
              .addTo(mapRef.current!)
              .bindPopup(popupHtml);
          });

          // Only draw transit polyline if query is a routing request or route_target marker is present
          const routeTarget = data.map_markers.find((m) => m.type === 'route_target' || (m.type === 'pfz' && data.user_query.toLowerCase().includes('route')));
          if (routeTarget) {
            if (routePolylineRef.current) {
              mapRef.current.removeLayer(routePolylineRef.current);
            }
            const polyline = L.polyline(
              [[resLat, resLon], [routeTarget.lat, routeTarget.lng]],
              { color: '#8b5cf6', weight: 3, dashArray: '6, 6', opacity: 0.9 }
            ).addTo(mapRef.current);
            routePolylineRef.current = polyline;
            mapRef.current.fitBounds(polyline.getBounds(), { padding: [45, 45] });
          }
        }

        // Add assistant message to multi-turn thread
        const assistantMsg: ChatMessage = {
          id: `ast_${Date.now()}`,
          role: 'assistant',
          text: data.recommendation,
          result: data,
          timestamp: new Date().toLocaleTimeString()
        };
        setChatHistory((prev) => [...prev, assistantMsg]);
      } else {
        alert(`Error: ${(data as any).detail || 'Failed to execute query.'}`);
      }
    } catch (err) {
      console.error(err);
      alert('Network error communicating with ORCA backend.');
    } finally {
      setLoading(false);
    }
  };

  const setPresetLocation = (lats: number, lons: number, name: string, sampleQuery?: string) => {
    setInputLat(lats);
    setInputLon(lons);
    setInputLocationName(name);
    setLocationSource('search');
    handleSetLocation(lats, lons, 'search', name);
    if (sampleQuery) {
      setQuery(sampleQuery);
    }
  };

  const getProvenanceCategory = (ev: Evidence) => {
    const src = (ev.source || '').toLowerCase();
    const srcType = (ev.source_type || '').toLowerCase();
    const st = (ev.status || '').toLowerCase();

    if (st === 'unavailable' || src.includes('unavailable') || src.includes('unauthenticated')) {
      return { label: 'UNAVAILABLE', badgeClass: 'bg-rose-950/80 text-rose-400 border border-rose-800' };
    }
    if (srcType === 'mock_adapter' || src.includes('mock') || src.includes('demo')) {
      return { label: 'MOCK/DEMO', badgeClass: 'bg-amber-950/80 text-amber-400 border border-amber-800' };
    }
    if (srcType === 'local_gis' || src.includes('gis') || src.includes('database') || src.includes('spatial')) {
      return { label: 'DATABASE', badgeClass: 'bg-blue-950/80 text-blue-400 border border-blue-800' };
    }
    if (srcType === 'derived_calculation' || st === 'forecast' || st === 'estimated' || st === 'derived' || src.includes('model') || src.includes('climatology')) {
      return { label: 'MODELLED', badgeClass: 'bg-purple-950/80 text-purple-400 border border-purple-800' };
    }
    if (srcType === 'real_api' || st === 'observed') {
      return { label: 'REAL/LIVE', badgeClass: 'bg-emerald-950/80 text-emerald-400 border border-emerald-800' };
    }
    return { label: 'MODELLED', badgeClass: 'bg-cyan-950/80 text-cyan-400 border border-cyan-800' };
  };

  return (
    <div className="min-h-screen bg-[#030914] text-slate-100 flex flex-col font-sans">
      {/* App Header */}
      <header className="flex items-center justify-between px-6 py-3.5 border-b border-cyan-950 bg-[#06101E] z-10">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-cyan-950/70 border border-cyan-800 text-marine-teal">
            <Anchor className="w-5 h-5 animate-pulse text-cyan-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-wide bg-gradient-to-r from-slate-50 to-cyan-400 bg-clip-text text-transparent">
              ORCA
            </h1>
            <p className="text-[9px] text-cyan-500 font-mono tracking-widest uppercase">
              Marine Decision Support & Multi-Turn Explainable Intelligence
            </p>
          </div>
        </div>
        
        {/* Navigation, DB & Tracer status header */}
        <div className="flex items-center space-x-3.5">
          <button
            onClick={handleGetLocation}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-cyan-950 border border-cyan-800 hover:border-cyan-600 rounded text-xs font-mono text-cyan-300 transition-colors"
          >
            <LocateFixed className="w-3.5 h-3.5 text-cyan-400" />
            My Geolocation
          </button>

          {/* MongoDB Persistence Status Badge */}
          <div className="flex items-center space-x-1.5 text-xs font-mono bg-cyan-950/40 border border-cyan-900 px-2.5 py-1 rounded">
            <Database className={`w-3.5 h-3.5 ${dbStatus.active ? 'text-emerald-400' : 'text-amber-400'}`} />
            <span className={dbStatus.active ? 'text-emerald-300' : 'text-amber-300'}>
              MONGO DB: {dbStatus.active ? 'CONNECTED' : 'MEMORY FALLBACK'}
            </span>
          </div>

          <div className="flex items-center space-x-1.5 text-xs font-mono">
            <Radio className={`w-3.5 h-3.5 ${wsStatus === 'connected' ? 'text-emerald-500 animate-ping' : 'text-rose-500'}`} />
            <span className={wsStatus === 'connected' ? 'text-emerald-400' : 'text-rose-400'}>
              TRACER: {wsStatus.toUpperCase()}
            </span>
          </div>
        </div>
      </header>

      {/* Main dashboard content area */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 p-4 overflow-hidden">
        {/* Left Side Pane: Multi-Turn Inquiry Console & Outcome */}
        <section className="lg:col-span-5 flex flex-col space-y-4 overflow-y-auto max-h-[84vh] pr-1">
          {/* Query input card */}
          <div className="glass-panel p-4 rounded-xl border border-cyan-950/80">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold tracking-wider text-cyan-400 uppercase flex items-center gap-2 font-mono">
                <Compass className="w-4 h-4" /> Multi-Turn Inquiry Console
              </h2>
              <div className="flex items-center space-x-2">
                <select 
                  value={lang} 
                  onChange={(e) => setLang(e.target.value)} 
                  className="bg-marine-navy border border-cyan-900 rounded px-2 py-1 text-xs text-cyan-300 font-mono focus:outline-none"
                >
                  <option value="en">English (EN)</option>
                  <option value="hi">Hindi (HI)</option>
                </select>
              </div>
            </div>

            <form onSubmit={handleQuery} className="space-y-3">


              {/* Application Active Location Status Banner */}
              <div className="bg-cyan-950/80 border border-cyan-700/80 p-2.5 rounded-lg text-xs font-mono shadow-md">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <MapPin className="w-4 h-4 text-cyan-400 animate-pulse" />
                    <span className="text-cyan-300 font-bold uppercase tracking-wide">Active Location:</span>
                    <span className="text-slate-100 font-mono font-bold">
                      {activeLocation.latitude.toFixed(4)}, {activeLocation.longitude.toFixed(4)}
                      {activeLocation.name ? ` (${activeLocation.name})` : ''}
                    </span>
                  </div>
                  <span className="text-[10px] text-cyan-300 bg-cyan-900/80 border border-cyan-700 px-2 py-0.5 rounded uppercase font-mono">
                    {activeLocation.source.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Manual Coordinate Inputs & Set Location Action */}
              <div className="space-y-2 bg-marine-navy/30 p-2.5 rounded-lg border border-cyan-950">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[10px] font-mono text-cyan-500 uppercase mb-1">Latitude (-90 to 90)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={inputLat}
                      onChange={(e) => {
                        setInputLat(parseFloat(e.target.value));
                        setLocationSource('manual_input');
                      }}
                      className="w-full bg-marine-navy border border-cyan-900 rounded p-1.5 text-xs font-mono text-slate-100 focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-[10px] font-mono text-cyan-500 uppercase mb-1">Longitude (-180 to 180)</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={inputLon}
                      onChange={(e) => {
                        setInputLon(parseFloat(e.target.value));
                        setLocationSource('manual_input');
                      }}
                      className="w-full bg-marine-navy border border-cyan-900 rounded p-1.5 text-xs font-mono text-slate-100 focus:border-cyan-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    type="button"
                    onClick={() => handleSetLocation()}
                    className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-3 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold font-mono text-xs rounded transition-all shadow-md shadow-cyan-950"
                  >
                    <MapPin className="w-3.5 h-3.5" />
                    Set Location
                  </button>
                  <button
                    type="button"
                    onClick={handleGetLocation}
                    className="flex items-center gap-1.5 py-1.5 px-3 bg-cyan-950 border border-cyan-800 hover:border-cyan-600 text-cyan-300 font-mono text-xs rounded transition-colors"
                  >
                    <LocateFixed className="w-3.5 h-3.5 text-cyan-400" />
                    GPS
                  </button>
                </div>

                {locationSuccessMsg && (
                  <div className="text-[11px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2.5 py-1 rounded flex items-center gap-1.5">
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                    {locationSuccessMsg}
                  </div>
                )}
              </div>

              {geoStatus !== 'idle' && (
                <div className="text-[10px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-900/60 px-2 py-1 rounded flex items-center justify-between">
                  <span>{geoStatus}</span>
                  {userLocation && <span className="text-emerald-400">±{Math.round(userLocation.accuracy || 0)}m</span>}
                </div>
              )}

              {/* Location Presets */}
              <div>
                <span className="block text-[9px] font-mono text-cyan-500 uppercase mb-1">Location Presets</span>
                <div className="flex flex-wrap gap-1.5">
                  <button 
                    type="button" 
                    onClick={() => setPresetLocation(12.91, 74.85, 'Mangalore Coast', 'Is it safe for me to go fishing tomorrow morning?')}
                    className="text-[10px] bg-cyan-950 border border-cyan-700 px-2 py-0.5 rounded text-cyan-300 hover:bg-cyan-900 font-mono font-bold"
                  >
                    📍 Mangalore (12.91, 74.85)
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setPresetLocation(22.50, 69.50, 'Gulf of Kutch', 'Which fishing zones should I avoid today?')}
                    className="text-[10px] bg-cyan-950/40 border border-cyan-900 px-2 py-0.5 rounded text-cyan-300 hover:bg-cyan-950 font-mono"
                  >
                    📍 Gulf of Kutch (22.5, 69.5)
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setPresetLocation(15.29, 73.98, 'Goa Coast', 'What are the weather and sea conditions at my location?')}
                    className="text-[10px] bg-cyan-950/40 border border-cyan-900 px-2 py-0.5 rounded text-cyan-300 hover:bg-cyan-950 font-mono"
                  >
                    📍 Goa (15.29, 73.98)
                  </button>
                  <button 
                    type="button" 
                    onClick={() => setPresetLocation(9.93, 76.26, 'Kochi Port', 'Is it safe to go fishing tomorrow morning?')}
                    className="text-[10px] bg-cyan-950/40 border border-cyan-900 px-2 py-0.5 rounded text-cyan-300 hover:bg-cyan-950 font-mono"
                  >
                    📍 Kochi (9.93, 76.26)
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-mono text-cyan-500 uppercase mb-1">Natural Language Request</label>
                <div className="relative">
                  <textarea
                    rows={2}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    className="w-full bg-marine-navy border border-cyan-900 rounded p-2.5 pr-10 text-xs focus:border-cyan-500 focus:outline-none resize-none"
                    placeholder="Ask about weather, sea conditions, fishing suitability, or follow up with 'What about tomorrow morning?'..."
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="absolute right-2 bottom-3 p-1.5 bg-cyan-950 border border-cyan-800 text-cyan-300 rounded hover:bg-cyan-900 transition-colors disabled:opacity-50"
                  >
                    {loading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            </form>
          </div>

          {/* Multi-Turn Thread Conversation Thread History */}
          <div className="glass-panel p-4 rounded-xl border border-cyan-950/80 space-y-2 max-h-48 overflow-y-auto">
            <div className="flex items-center justify-between border-b border-cyan-950 pb-1.5">
              <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-cyan-400" /> Multi-Turn Conversation ({chatHistory.length} turns)
              </h3>
              <button
                type="button"
                onClick={async () => {
                  const newId = `session_${Date.now()}`;
                  clientId.current = newId;
                  setChatHistory([]);
                  setResult(null);
                  setTraceLogs([]);
                  try {
                    await fetch('/api/query', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        query: 'reset',
                        latitude: activeLocation.latitude,
                        longitude: activeLocation.longitude,
                        conversation_id: newId,
                        reset: true
                      })
                    });
                  } catch (e) {
                    console.warn('New chat reset error:', e);
                  }
                }}
                className="text-[10px] font-mono bg-red-950/60 border border-red-800 text-red-300 hover:bg-red-900 px-2.5 py-0.5 rounded transition-colors flex items-center gap-1 font-bold"
              >
                <span>+ NEW CHAT</span>
              </button>
            </div>
            {chatHistory.length > 0 ? (
              <div className="space-y-2 font-mono text-[11px]">
                {chatHistory.map((msg) => (
                  <div key={msg.id} className={`p-2 rounded border text-xs ${msg.role === 'user' ? 'bg-cyan-950/40 border-cyan-900 text-cyan-200 ml-4' : 'bg-marine-navy/60 border-cyan-950 text-slate-100 mr-4'}`}>
                    <div className="flex justify-between text-[9px] text-cyan-500 mb-1 font-bold">
                      <span>{msg.role === 'user' ? 'USER INQUIRY' : 'ORCA DECISION'}</span>
                      <span>{msg.timestamp}</span>
                    </div>
                    <p className="leading-relaxed">{msg.text}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[10px] font-mono text-slate-500 italic py-1">
                New conversation started. Context reset.
              </div>
            )}
          </div>

          {/* OSRM Prototype Route Calculation Console */}
          <div className="glass-panel p-4 rounded-xl border border-cyan-950/80 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5" /> OSRM Road Routing Prototype & Geofence Check
              </h3>
              <button
                type="button"
                onClick={() => setIsRoutingMode(!isRoutingMode)}
                className="text-[10px] font-mono text-cyan-500 underline"
              >
                {isRoutingMode ? 'Hide Options' : 'Show Options'}
              </button>
            </div>

            {isRoutingMode && (
              <div className="space-y-2 pt-1 border-t border-cyan-950/60">
                <div className="text-[10px] font-mono text-amber-400 bg-amber-950/30 p-1.5 rounded border border-amber-900/40">
                  NOTICE: Prototype path generated via OSRM. Marine navigability (bathymetry/shipping channels) is NOT verified.
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div>
                    <label className="block text-[9px] text-cyan-600 uppercase">Dest Lat</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={destLat}
                      onChange={(e) => setDestLat(parseFloat(e.target.value))}
                      className="w-full bg-marine-navy border border-cyan-900 rounded p-1.5 text-xs text-slate-100"
                    />
                  </div>
                  <div>
                    <label className="block text-[9px] text-cyan-600 uppercase">Dest Lon</label>
                    <input
                      type="number"
                      step="0.0001"
                      value={destLon}
                      onChange={(e) => setDestLon(parseFloat(e.target.value))}
                      className="w-full bg-marine-navy border border-cyan-900 rounded p-1.5 text-xs text-slate-100"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleCalculateRoute}
                  disabled={routeLoading}
                  className="w-full py-1.5 bg-cyan-950 border border-cyan-700 rounded text-xs font-mono font-bold text-cyan-300 hover:bg-cyan-900 flex items-center justify-center gap-1.5"
                >
                  {routeLoading ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Navigation className="w-3 h-3" />}
                  Calculate OSRM Prototype Path
                </button>

                {routeData && (
                  <div className="bg-marine-navy/40 border border-cyan-900 p-2.5 rounded text-[11px] font-mono space-y-1">
                    <div className="flex justify-between font-bold">
                      <span>Status: <span className={routeData.status === 'ROUTE_CONFLICT' ? 'text-rose-400' : 'text-cyan-300'}>{routeData.status}</span></span>
                      <span>Distance: {routeData.distance_km} km ({routeData.distance_nm} NM)</span>
                    </div>
                    <div className="text-[10px] text-slate-400">Bearing: {routeData.bearing_degrees}° | ETA: {routeData.eta_hours} hrs | Navigability: <span className="text-amber-400">Unverified</span></div>
                    {routeData.warnings && routeData.warnings.length > 0 && (
                      <div className="text-rose-300 text-[10px] mt-1 bg-rose-950/40 p-1.5 rounded border border-rose-900">
                        {routeData.warnings.join(' ')}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Outcome response panel */}
          {result && (
            <div className="glass-panel p-4 rounded-xl border border-cyan-950 space-y-3">
              <div className="flex items-center justify-between border-b border-cyan-950/60 pb-2">
                <h3 className="text-xs font-mono text-cyan-500 uppercase tracking-wider">Primary Recommendation</h3>
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                    result.safety_rating === 'safe' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
                    result.safety_rating === 'caution' ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                    'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {result.safety_rating}
                  </span>
                  <span className="text-xs font-mono text-cyan-400">
                    Confidence: {(result.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>

              {/* Primary Action Recommendation */}
              <div className="bg-cyan-950/40 border border-cyan-900/60 p-3 rounded-lg">
                <p className="text-sm font-semibold text-white">{result.recommendation}</p>
              </div>

              {/* EXPLAINABLE AI PANEL ("Why ORCA Made This Decision") */}
              <div className="bg-[#051326] border border-cyan-900/80 rounded-lg p-3 space-y-2">
                <div 
                  onClick={() => setShowXAI(!showXAI)}
                  className="flex items-center justify-between cursor-pointer border-b border-cyan-950 pb-1.5"
                >
                  <h4 className="text-xs font-mono font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> Why ORCA Made This Decision (Explainable AI Panel)
                  </h4>
                  {showXAI ? <ChevronDown className="w-4 h-4 text-cyan-400" /> : <ChevronRight className="w-4 h-4 text-cyan-400" />}
                </div>

                {showXAI && result.explainability_factors && (
                  <div className="space-y-2 pt-1 font-mono text-[11px]">
                    <div className="grid grid-cols-2 gap-2 bg-marine-navy/40 p-2 rounded border border-cyan-950">
                      <div>Deterministic Score: <span className="font-bold text-cyan-300">{result.deterministic_score}/100</span></div>
                      <div>Grounded Confidence: <span className="font-bold text-emerald-400">{(result.confidence * 100).toFixed(0)}%</span></div>
                      <div>MongoDB Persistence: <span className={result.persisted ? 'text-emerald-400' : 'text-amber-400'}>{result.persisted ? 'PERSISTED' : 'MEMORY FALLBACK'}</span></div>
                      <div>Agents Executed: <span className="text-cyan-200">{result.agents_executed.length} agents</span></div>
                    </div>

                    <div className="space-y-1.5 max-h-44 overflow-y-auto">
                      {result.explainability_factors.map((factor, idx) => (
                        <div key={idx} className="bg-marine-navy/20 border border-cyan-950 p-2 rounded space-y-0.5">
                          <div className="flex justify-between font-bold">
                            <span className="text-cyan-400">{factor.title}</span>
                            <span className={factor.status === 'danger' ? 'text-rose-400' : factor.status === 'warning' ? 'text-amber-400' : 'text-emerald-400'}>
                              {factor.value}
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-300 font-sans">{factor.description}</p>
                          <div className="text-[9px] text-slate-500">Source: {factor.source}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Natural Language Explanation */}
              <div className="space-y-1">
                <h4 className="text-xs font-bold text-cyan-300 font-mono uppercase tracking-wider">Factual Justification</h4>
                <p className="text-xs text-slate-300 leading-relaxed font-light">{result.explanation}</p>
              </div>

              {/* Traceable Evidence Panel */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-cyan-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5" /> Structured Evidence (Click to inspect provenance)
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {result.evidence.map((ev) => {
                    const cat = getProvenanceCategory(ev);
                    return (
                      <div 
                        key={ev.id} 
                        onClick={() => setSelectedEvidence(ev)}
                        className="bg-marine-navy/40 border border-cyan-950 hover:border-cyan-800 cursor-pointer rounded p-2 text-[11px] font-mono transition-colors"
                      >
                        <div className="flex justify-between items-center text-cyan-400 border-b border-cyan-950/40 pb-1 mb-1 font-bold">
                          <span>{ev.parameter.replace(/_/g, ' ').toUpperCase()}</span>
                          <span className={`text-[9px] px-1.5 py-0.5 rounded font-mono uppercase ${cat.badgeClass}`}>
                            {cat.label} ({ev.status})
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-y-0.5 text-slate-400 text-[10px]">
                          <div>Value: <span className="text-slate-100 font-bold">{typeof ev.value === 'object' ? JSON.stringify(ev.value) : String(ev.value)} {ev.unit}</span></div>
                          <div>Source: <span className="text-slate-100">{ev.source}</span></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </section>

        {/* Right Side Pane: Interactive Map & Trace Console */}
        <section className="lg:col-span-7 flex flex-col space-y-4 h-[84vh]">
          {/* Map panel */}
          <div className="flex-1 glass-panel rounded-xl overflow-hidden relative border border-cyan-950">
            {/* Map Header Overlay Controls */}
            <div className="absolute top-3 left-3 bg-[#0a192fc0] border border-cyan-900 rounded p-2 z-[400] text-[10px] font-mono flex items-center gap-3">
              <div>
                <span className="font-bold text-cyan-400 block">GEOSPATIAL CANVAS</span>
                <span className="text-slate-400">OpenStreetMap Standard</span>
              </div>

              <button
                onClick={() => setShowLayerPanel(!showLayerPanel)}
                className="flex items-center gap-1 bg-cyan-950 border border-cyan-700 px-2 py-1 rounded text-cyan-300 hover:bg-cyan-900"
              >
                <Layers className="w-3 h-3" /> Layers Control
              </button>
            </div>

            {/* Layer Panel Dropdown */}
            {showLayerPanel && (
              <div className="absolute top-12 left-3 bg-[#06101Ee0] backdrop-blur-md border border-cyan-800 rounded-lg p-3 z-[450] text-xs font-mono w-72 space-y-2 shadow-2xl">
                <div className="flex items-center justify-between border-b border-cyan-900 pb-1.5">
                  <span className="font-bold text-cyan-300">Map Data Layers</span>
                  <button onClick={() => setShowLayerPanel(false)}><X className="w-3.5 h-3.5 text-slate-400" /></button>
                </div>
                <div className="space-y-1.5 max-h-60 overflow-y-auto">
                  {mapLayers.map((lyr) => (
                    <div key={lyr.id} className="flex items-center justify-between text-[11px]">
                      <label className="flex items-center space-x-2 text-slate-200 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={activeLayers[lyr.id] ?? true}
                          onChange={(e) => setActiveLayers({ ...activeLayers, [lyr.id]: e.target.checked })}
                          disabled={lyr.status === 'unavailable'}
                          className="rounded border-cyan-900 text-cyan-500 bg-marine-navy"
                        />
                        <span>{lyr.name}</span>
                      </label>
                      <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono ${lyr.status === 'available' ? 'text-emerald-400 bg-emerald-950/60' : 'text-rose-400 bg-rose-950/60'}`}>
                        {lyr.status.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Map Container */}
            <div ref={mapContainerRef} className="w-full h-full min-h-[420px] z-0" />
          </div>

          {/* Real Live Execution Trace Console */}
          <div className="glass-panel p-4 rounded-xl border border-cyan-950 h-44 flex flex-col">
            <div className="flex items-center justify-between border-b border-cyan-950/70 pb-1.5 mb-2 shrink-0">
              <span className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5" /> Real Live Execution Trace Console
              </span>
              <span className="text-[10px] text-slate-500 font-mono">
                session_id: {clientId.current}
              </span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-1.5 font-mono text-[11px]">
              {traceLogs.length === 0 && !loading && (
                <div className="text-slate-500 flex flex-col items-center justify-center h-full space-y-1">
                  <Terminal className="w-4 h-4 text-cyan-950" />
                  <span>Trace console idle. Submit a query to inspect live agent execution.</span>
                </div>
              )}
              {traceLogs.map((log, idx) => (
                <div key={idx} className="bg-marine-navy/20 border border-cyan-950/60 p-2 rounded flex items-start space-x-2">
                  <span className="text-[9px] text-cyan-600 mt-0.5">[{log.timestamp}]</span>
                  <div className="flex-1 space-y-0.5">
                    <div className="text-cyan-400 font-bold uppercase tracking-wider text-[10px]">
                      {log.event_type}
                    </div>
                    <pre className="text-slate-300 font-sans whitespace-pre-wrap leading-relaxed text-[11px]">
                      {JSON.stringify(log.payload, null, 2)}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Evidence Provenance Modal */}
      {selectedEvidence && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-[999]">
          <div className="glass-panel max-w-lg w-full p-6 rounded-xl border border-cyan-700 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-cyan-900 pb-3">
              <h3 className="text-sm font-mono font-bold text-cyan-300 uppercase tracking-wider flex items-center gap-2">
                <Info className="w-4 h-4 text-cyan-400" /> Evidence Provenance Detail
              </h3>
              <button onClick={() => setSelectedEvidence(null)}><X className="w-5 h-5 text-slate-400 hover:text-white" /></button>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="bg-marine-navy p-3 rounded border border-cyan-900 space-y-1">
                <div className="flex justify-between items-center">
                  <span className="text-cyan-400 font-bold">Parameter: {selectedEvidence.parameter}</span>
                  <span className={`text-[10px] px-2 py-0.5 rounded font-mono font-bold uppercase ${getProvenanceCategory(selectedEvidence).badgeClass}`}>
                    {getProvenanceCategory(selectedEvidence).label}
                  </span>
                </div>
                <div>Value: <span className="text-white font-bold">{typeof selectedEvidence.value === 'object' ? JSON.stringify(selectedEvidence.value, null, 2) : String(selectedEvidence.value)}</span> {selectedEvidence.unit}</div>
                <div>Status: <span className={selectedEvidence.status === 'unavailable' ? 'text-rose-400 font-bold' : 'text-emerald-400'}>{selectedEvidence.status}</span></div>
                <div>Confidence: {((selectedEvidence.confidence ?? 1.0) * 100).toFixed(0)}%</div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-slate-300">
                <div>Source: <span className="text-cyan-200">{selectedEvidence.source}</span></div>
                <div>Source Type: <span className="text-cyan-200">{selectedEvidence.source_type}</span></div>
                <div>Agent: <span className="text-cyan-200">{selectedEvidence.agent || 'N/A'}</span></div>
                <div>Tool: <span className="text-cyan-200">{selectedEvidence.tool || 'N/A'}</span></div>
                <div>Retrieved At: <span className="text-cyan-200">{new Date(selectedEvidence.retrieved_at).toLocaleString()}</span></div>
                {selectedEvidence.source_url && (
                  <div className="col-span-2 truncate">Source URL: <a href={selectedEvidence.source_url} target="_blank" rel="noreferrer" className="text-cyan-400 underline">{selectedEvidence.source_url}</a></div>
                )}
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedEvidence(null)}
                className="px-4 py-1.5 bg-cyan-950 border border-cyan-700 rounded text-xs font-mono text-cyan-300 hover:bg-cyan-900"
              >
                Close Provenance
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
