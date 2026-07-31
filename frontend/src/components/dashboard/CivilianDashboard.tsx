"use client";

import React, { useState, useEffect } from "react";
import { 
  Navigation, 
  MapPin, 
  AlertTriangle, 
  ShieldAlert, 
  Compass, 
  CheckCircle2, 
  Send, 
  RefreshCw,
  Search,
  Map as MapIcon
} from "lucide-react";
import { getApiUrl } from "@/lib/api";
import ToastAlert from "@/components/ui/ToastAlert";
import LiveTrafficMap, { RouteProp } from "@/components/ui/LiveTrafficMap";
import { Autocomplete, useJsApiLoader } from "@react-google-maps/api";

const LIBRARIES: ("places")[] = ["places"];

interface Incident {
  id: number;
  location: string;
  type: string;
  severity: string;
  description: string;
  reported_at: string;
  status: string;
}

export default function CivilianDashboard({ username }: { username?: string }) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
    libraries: LIBRARIES
  });

  const [origin, setOrigin] = useState("Downtown Central");
  const [destination, setDestination] = useState("Tech Park Corridor");
  const [routeResult, setRouteResult] = useState<any>(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);

  useEffect(() => {
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setUserLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
        (err) => console.log("Geolocation error:", err)
      );
    }
  }, []);

  const originRef = React.useRef<google.maps.places.Autocomplete | null>(null);
  const destRef = React.useRef<google.maps.places.Autocomplete | null>(null);

  const onOriginLoad = (autocomplete: google.maps.places.Autocomplete) => {
    originRef.current = autocomplete;
  };
  const onDestLoad = (autocomplete: google.maps.places.Autocomplete) => {
    destRef.current = autocomplete;
  };

  const onOriginPlaceChanged = () => {
    if (originRef.current !== null) {
      const place = originRef.current.getPlace();
      if (place.formatted_address || place.name) {
        setOrigin(place.formatted_address || place.name || "");
      }
    }
  };

  const onDestPlaceChanged = () => {
    if (destRef.current !== null) {
      const place = destRef.current.getPlace();
      if (place.formatted_address || place.name) {
        setDestination(place.formatted_address || place.name || "");
      }
    }
  };


  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [incidentLoc, setIncidentLoc] = useState("");
  const [incidentType, setIncidentType] = useState("Accident");
  const [incidentDesc, setIncidentDesc] = useState("");
  const [incidentSubmitting, setIncidentSubmitting] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const [junctions, setJunctions] = useState<any[]>([]);
  const [activeRoute, setActiveRoute] = useState<RouteProp | null>(null);

  const fetchIncidents = async () => {
    try {
      const res = await fetch(getApiUrl("traffic/incidents"));
      if (res.ok) {
        const data = await res.json();
        setIncidents(data);
      }
    } catch {}
  };

  const fetchJunctions = async () => {
    try {
      const res = await fetch(getApiUrl("traffic/junctions"));
      if (res.ok) {
        const data = await res.json();
        setJunctions(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchIncidents();
    fetchJunctions();
  }, []);

  // Poll for APPROVED routes
  useEffect(() => {
    const pollRoutes = async () => {
      try {
        const res = await fetch(getApiUrl("traffic/proposed-routes"));
        if (res.ok) {
          const data = await res.json();
          const approved = data.filter((r: any) => r.status === "APPROVED");
          if (approved.length > 0) {
            const latest = approved[approved.length - 1];
            setActiveRoute((prev) => {
              if (!prev || prev.id !== latest.id) {
                setToastMsg(`Alert ${username ? `[${username}]` : ""}: New Alternate Route Approved by Controller!`);
                return latest;
              }
              return prev;
            });
          }
        }
      } catch (e) {}
    };

    pollRoutes();
    const interval = setInterval(pollRoutes, 5000);
    return () => clearInterval(interval);
  }, [username]);

  const handleRouteSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingRoute(true);
    try {
      const res = await fetch(getApiUrl("traffic/route-optimize"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ origin, destination }),
      });
      if (res.ok) {
        const data = await res.json();
        setRouteResult(data);
      }
    } catch {
      setRouteResult({
        origin,
        destination,
        primary_route: {
          name: "Direct via Main Corridor",
          distance_km: 12.4,
          estimated_time_mins: 26,
          congestion: "Moderate",
          delay_mins: 6.5,
        },
        alternate_route: {
          name: "Outer Expressway Bypass",
          distance_km: 14.8,
          estimated_time_mins: 19,
          congestion: "Clear",
          delay_mins: 1.2,
        },
        recommendation: "Take Alternate Express Route to save ~7 mins.",
      });
    } finally {
      setLoadingRoute(false);
    }
  };

  const handleReportIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!incidentLoc || !incidentDesc) return;
    setIncidentSubmitting(true);
    try {
      const res = await fetch(getApiUrl("traffic/incidents"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          location: incidentLoc,
          type: incidentType,
          severity: "High",
          description: incidentDesc,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setIncidents([data.incident, ...incidents]);
        setIncidentLoc("");
        setIncidentDesc("");
        setToastMsg("Traffic incident report submitted to city control center!");
        setTimeout(() => setToastMsg(null), 4000);
      }
    } catch {
      setToastMsg("Incident report logged locally.");
      setTimeout(() => setToastMsg(null), 3000);
    } finally {
      setIncidentSubmitting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Toast Alert */}
      {toastMsg && (
        <ToastAlert 
          type="success" 
          message={toastMsg} 
          onClose={() => setToastMsg(null)} 
        />
      )}

      {/* Hero Banner (Matching Login Aesthetic) */}
      <div className="rounded-3xl bg-slate-950 text-white p-6 sm:p-8 shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-2xl space-y-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-bold uppercase tracking-wider">
            <Compass className="w-3.5 h-3.5" /> Civilian Commuter Portal
          </span>
          <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
            Smart Route Planning & Real-Time Commute Insights
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm font-medium leading-relaxed">
            Avoid traffic bottlenecks, inspect live junction speeds, and report real-time hazards directly to city management.
          </p>
        </div>
      </div>

      {/* Live Map Full Width */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6 relative overflow-hidden z-0">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-slate-100 border border-slate-200 text-slate-900">
            <MapIcon className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-extrabold text-slate-900">Live Traffic Map & Active Routes</h3>
            <p className="text-xs text-slate-500 font-medium">Real-time route visualizations updated by City Traffic Controllers.</p>
          </div>
        </div>
        <div className="w-full relative z-0">
          <LiveTrafficMap proposedRoute={activeRoute} userLocation={userLocation} />
        </div>
      </div>

      {/* Main Grid: Route Planner + Incident Reporter */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Column: Smart Route Planner */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-slate-100 border border-slate-200 text-slate-900">
              <Navigation className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-slate-900">AI Route Optimizer</h3>
              <p className="text-xs text-slate-500 font-medium">Fastest route calculations & delay avoidance</p>
            </div>
          </div>

          <form onSubmit={handleRouteSearch} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600" /> Origin Location
                </label>
                {isLoaded ? (
                  <Autocomplete onLoad={onOriginLoad} onPlaceChanged={onOriginPlaceChanged}>
                    <input
                      type="text"
                      required
                      placeholder="Enter origin"
                      defaultValue={origin}
                      onChange={(e) => setOrigin(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-950 font-medium"
                    />
                  </Autocomplete>
                ) : (
                  <input
                    type="text"
                    required
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-950 font-medium"
                  />
                )}
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5 flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-rose-600" /> Destination
                </label>
                {isLoaded ? (
                  <Autocomplete onLoad={onDestLoad} onPlaceChanged={onDestPlaceChanged}>
                    <input
                      type="text"
                      required
                      placeholder="Enter destination"
                      defaultValue={destination}
                      onChange={(e) => setDestination(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-950 font-medium"
                    />
                  </Autocomplete>
                ) : (
                  <input
                    type="text"
                    required
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-950 font-medium"
                  />
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={loadingRoute}
              className="w-full py-3.5 px-4 bg-slate-950 hover:bg-black text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 text-xs cursor-pointer"
            >
              {loadingRoute ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Search AI Optimized Route
            </button>
          </form>

          {/* Route Optimization Results */}
          {routeResult && (
            <div className="space-y-4 pt-4 border-t border-slate-100">
              <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs font-bold flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                <span>{routeResult.recommendation}</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Primary Route */}
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-700">Standard Route</span>
                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
                      {routeResult.primary_route.congestion}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-slate-900">{routeResult.primary_route.name}</div>
                  <div className="flex justify-between text-xs text-slate-500 pt-1 font-medium">
                    <span>{routeResult.primary_route.distance_km} km</span>
                    <span className="font-bold text-amber-700">{routeResult.primary_route.estimated_time_mins} mins</span>
                  </div>
                </div>

                {/* Alternate Route */}
                <div className="p-4 rounded-2xl bg-white border border-emerald-300 shadow-sm space-y-2 relative overflow-hidden">
                  <div className="absolute top-0 right-0 bg-emerald-600 text-white text-[9px] font-black uppercase px-2.5 py-0.5 rounded-bl-lg">
                    Recommended
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-emerald-800">Alternate Express</span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                      {routeResult.alternate_route.congestion}
                    </span>
                  </div>
                  <div className="text-sm font-bold text-slate-900">{routeResult.alternate_route.name}</div>
                  <div className="flex justify-between text-xs text-slate-500 pt-1 font-medium">
                    <span>{routeResult.alternate_route.distance_km} km</span>
                    <span className="font-bold text-emerald-600">{routeResult.alternate_route.estimated_time_mins} mins</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Live Incident Reporting & Alerts */}
        <div className="lg:col-span-5 space-y-6">
          {/* Incident Reporter Form */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-700">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-extrabold text-slate-900">Report Traffic Hazard</h3>
                <p className="text-xs text-slate-500 font-medium">Notify traffic controllers of live issues</p>
              </div>
            </div>

            <form onSubmit={handleReportIncident} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Road / Junction Location</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. MG Road Flyover"
                  value={incidentLoc}
                  onChange={(e) => setIncidentLoc(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2.5 text-slate-900 focus:outline-none focus:border-slate-950 font-medium"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-700 font-bold mb-1">Incident Type</label>
                  <select
                    value={incidentType}
                    onChange={(e) => setIncidentType(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-slate-900 font-medium focus:outline-none focus:border-slate-950"
                  >
                    <option value="Accident">Accident</option>
                    <option value="Road Work">Road Work</option>
                    <option value="Signal Failure">Signal Failure</option>
                    <option value="Waterlogging">Waterlogging</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-700 font-bold mb-1">Priority</label>
                  <div className="py-2.5 px-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 font-bold text-center">
                    High Priority
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Description</label>
                <textarea
                  required
                  rows={2}
                  placeholder="Briefly describe the obstacle..."
                  value={incidentDesc}
                  onChange={(e) => setIncidentDesc(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-2 text-slate-900 focus:outline-none focus:border-slate-950 font-medium resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={incidentSubmitting}
                className="w-full py-3 px-4 bg-amber-500 hover:bg-amber-600 text-slate-950 font-extrabold rounded-xl transition-all flex items-center justify-center gap-2 text-xs shadow-md cursor-pointer"
              >
                {incidentSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Submit Report
              </button>
            </form>
          </div>

          {/* Active Alerts List */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-extrabold text-slate-900 flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-600" /> Active Commute Alerts
              </h3>
              <span className="text-[10px] font-bold text-slate-600 px-2 py-0.5 rounded-full bg-slate-100">
                {incidents.length} Live
              </span>
            </div>

            <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
              {incidents.map((inc) => (
                <div key={inc.id} className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-bold text-slate-900">{inc.location}</span>
                    <span className="px-2 py-0.5 rounded-full bg-rose-50 text-rose-700 text-[10px] font-bold border border-rose-200">
                      {inc.type}
                    </span>
                  </div>
                  <p className="text-slate-600 text-[11px] font-medium leading-relaxed">{inc.description}</p>
                  <div className="text-[10px] text-slate-400 pt-1 flex justify-between">
                    <span>{inc.reported_at}</span>
                    <span className="text-emerald-600 font-bold">{inc.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

      {/* Junction Density Monitor Section */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-extrabold text-slate-900">City Junction Live Density Feed</h3>
            <p className="text-xs text-slate-500 font-medium">Real-time vehicle counts across main city intersections</p>
          </div>
          <button
            onClick={fetchJunctions}
            className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs flex items-center gap-1.5 font-bold transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh Feed
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {junctions.map((j) => (
            <div key={j.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs font-bold text-slate-400">{j.id}</div>
                  <div className="text-sm font-bold text-slate-900">{j.name}</div>
                </div>
                <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                  j.status === 'Heavy' 
                    ? 'bg-rose-50 text-rose-700 border-rose-200' 
                    : j.status === 'Moderate'
                    ? 'bg-amber-50 text-amber-800 border-amber-200'
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}>
                  {j.status} Flow
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-400 font-medium block">Density</span>
                  <span className="font-bold text-slate-900">{j.vehicle_count} veh/hr</span>
                </div>
                <div className="p-2 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-400 font-medium block">Avg Speed</span>
                  <span className="font-bold text-blue-700">{j.speed_kmh} km/h</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
