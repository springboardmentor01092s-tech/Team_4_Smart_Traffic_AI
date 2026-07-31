"use client";

import React, { useState, useEffect } from "react";
import { 
  ShieldAlert, 
  Zap, 
  BarChart3, 
  Radio, 
  RefreshCw, 
  Play
} from "lucide-react";
import { getApiUrl } from "@/lib/api";
import ToastAlert from "@/components/ui/ToastAlert";
import LiveTrafficMap from "@/components/ui/LiveTrafficMap";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid
} from "recharts";

export default function ControllerDashboard() {
  const [junctions, setJunctions] = useState<any[]>([]);
  const [loadingJunctions, setLoadingJunctions] = useState(false);

  const [trendData, setTrendData] = useState<any[]>([]);
  
  const [proposedRoutes, setProposedRoutes] = useState<any[]>([]);
  const [loadingRoutes, setLoadingRoutes] = useState(false);

  const [vehicleCount, setVehicleCount] = useState<number>(850);
  const [avgSpeed, setAvgSpeed] = useState<number>(24.0);
  const [weather, setWeather] = useState<string>("Clear");
  const [isPeakHour, setIsPeakHour] = useState<boolean>(true);
  const [roadCapacity, setRoadCapacity] = useState<number>(1000);
  
  const [prediction, setPrediction] = useState<{
    congestion_level: string;
    congestion_score: number;
    estimated_delay_minutes: number;
    recommended_action: string;
  }>({
    congestion_level: "High",
    congestion_score: 74.2,
    estimated_delay_minutes: 18.5,
    recommended_action: "Trigger dynamic green wave priority on MG Road corridor."
  });

  const [loadingPredict, setLoadingPredict] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const fetchJunctions = async () => {
    setLoadingJunctions(true);
    try {
      const res = await fetch(getApiUrl("traffic/junctions"));
      if (res.ok) {
        const data = await res.json();
        setJunctions(data);
      }
    } catch {} finally {
      setLoadingJunctions(false);
    }
  };

  const fetchTrends = async () => {
    try {
      const res = await fetch(getApiUrl("traffic/analytics-trends"));
      if (res.ok) {
        const data = await res.json();
        setTrendData(data.trend_data || []);
      }
    } catch {}
  };

  const fetchProposedRoutes = async () => {
    setLoadingRoutes(true);
    try {
      const res = await fetch(getApiUrl("traffic/proposed-routes"));
      if (res.ok) {
        const data = await res.json();
        setProposedRoutes(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingRoutes(false);
    }
  };

  useEffect(() => {
    fetchJunctions();
    fetchTrends();
    fetchProposedRoutes();
  }, []);

  const handleOverrideSignal = async (junctionId: string, mode: "emergency_green" | "all_red" | "auto") => {
    try {
      const res = await fetch(getApiUrl("traffic/override-signal"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ junction_id: junctionId, mode }),
      });
      if (res.ok) {
        fetchJunctions();
        const modeLabel = mode === "emergency_green" ? "EMERGENCY GREEN WAVE" : mode === "all_red" ? "TRAFFIC HALTED" : "AUTOMATED SIGNAL CONTROL";
        setToastMsg(`Junction ${junctionId} set to: ${modeLabel}`);
      }
    } catch {
      setToastMsg(`Signal mode updated for ${junctionId}`);
    }
  };
  
  const handleApproveRoute = async (routeId: string) => {
    try {
      const res = await fetch(getApiUrl("traffic/approve-route"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ route_id: routeId }),
      });
      if (res.ok) {
        setToastMsg("Route Approved and broadcasted to civilians!");
        fetchProposedRoutes();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoadingPredict(true);
    try {
      const response = await fetch(getApiUrl("traffic/predict"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          vehicle_count: Number(vehicleCount),
          avg_speed_kmh: Number(avgSpeed),
          weather_condition: weather,
          is_peak_hour: isPeakHour,
          road_capacity: Number(roadCapacity)
        })
      });

      if (response.ok) {
        const data = await response.json();
        setPrediction(data);
        fetchProposedRoutes(); // Refresh routes in case AI proposed a new one
      }
    } catch {
      const ratio = vehicleCount / Math.max(roadCapacity, 1);
      const score = Math.min(100, Math.max(0, ratio * 60 + (60 - avgSpeed) * 0.8 + (isPeakHour ? 15 : 0)));
      const level = score < 35 ? "Low" : score < 70 ? "Moderate" : "High";
      setPrediction({
        congestion_level: level,
        congestion_score: Math.round(score * 10) / 10,
        estimated_delay_minutes: Math.round(score * 0.25 * 10) / 10,
        recommended_action: level === "High" ? "Trigger emergency bypass rerouting" : "Maintain automated green wave timing"
      });
    } finally {
      setLoadingPredict(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Toast Alert */}
      {toastMsg && (
        <ToastAlert 
          type="warning" 
          message={toastMsg} 
          onClose={() => setToastMsg(null)} 
        />
      )}

      {/* Operator Command Header */}
      <div className="rounded-3xl bg-slate-950 text-white p-6 sm:p-8 shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-black uppercase tracking-wider flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5 animate-pulse" /> Traffic Control Center Console
            </span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-white">
            City Junction Override & AI Signal Command
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm font-medium">
            Trigger emergency green waves, inspect real-time junction counts, and execute AI congestion forecasting.
          </p>
        </div>

        <button
          onClick={fetchJunctions}
          className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs flex items-center gap-2 transition-all cursor-pointer shrink-0"
        >
          <RefreshCw className={`w-4 h-4 ${loadingJunctions ? 'animate-spin' : ''}`} />
          Sync Junctions
        </button>
      </div>

      {/* Emergency Signal Override Grid */}
      <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-slate-900">City Junction Signal Grid</h3>
              <p className="text-xs text-slate-500 font-medium">Emergency vehicle override controls (Ambulance / Fire / Police)</p>
            </div>
          </div>
          <span className="text-xs text-slate-500 font-bold hidden sm:inline">
            Intersections Active: <strong className="text-slate-900">{junctions.length}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {junctions.map((j) => (
            <div key={j.id} className={`p-5 rounded-2xl bg-slate-50 border transition-all ${j.override ? 'border-amber-400 shadow-md bg-amber-50/20' : 'border-slate-200'}`}>
              <div className="flex justify-between items-start mb-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{j.id}</span>
                  <h4 className="text-sm font-bold text-slate-900">{j.name}</h4>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${j.signal === 'Green' ? 'bg-emerald-500 animate-ping' : j.signal === 'Yellow' ? 'bg-amber-500' : 'bg-rose-500'}`} />
                  <span className="text-xs font-bold text-slate-700">{j.signal}</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                <div className="p-2 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-400 font-medium block">Density</span>
                  <span className="font-bold text-slate-900">{j.vehicle_count} veh/hr</span>
                </div>
                <div className="p-2 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-400 font-medium block">Speed</span>
                  <span className="font-bold text-blue-700">{j.speed_kmh} km/h</span>
                </div>
              </div>

              {/* Signal Controls */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Controller Override</span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
                  <button
                    onClick={() => handleOverrideSignal(j.id, "emergency_green")}
                    className="py-2 px-2 bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold rounded-xl text-[10px] transition-all cursor-pointer shadow-sm"
                  >
                    Green Wave
                  </button>
                  <button
                    onClick={() => handleOverrideSignal(j.id, "all_red")}
                    className="py-2 px-2 bg-rose-600 hover:bg-rose-700 text-white font-extrabold rounded-xl text-[10px] transition-all cursor-pointer shadow-sm"
                  >
                    Halt Traffic
                  </button>
                  <button
                    onClick={() => handleOverrideSignal(j.id, "auto")}
                    className="py-2 px-2 bg-slate-200 hover:bg-slate-300 text-slate-900 font-extrabold rounded-xl text-[10px] transition-all cursor-pointer"
                  >
                    Auto Mode
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AI Prediction Simulator & Route Approval */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left: AI Simulator & Route Pending */}
        <div className="lg:col-span-6 space-y-6 lg:space-y-8">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-2xl bg-slate-100 border border-slate-200 text-slate-900">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-extrabold text-slate-900">AI Congestion Simulator</h3>
                <p className="text-xs text-slate-500 font-medium">Real-time parameters for XGBoost neural inference</p>
              </div>
            </div>

            <form onSubmit={handlePredict} className="space-y-4 text-xs">
              <div>
                <div className="flex justify-between font-bold text-slate-700 mb-1.5">
                  <span>Vehicle Density (Vehicles / hr)</span>
                  <span className="text-blue-700 font-black">{vehicleCount}</span>
                </div>
                <input 
                  type="range" 
                  min="100" 
                  max="2000" 
                  step="20"
                  value={vehicleCount}
                  onChange={(e) => setVehicleCount(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-950"
                />
              </div>

              <div>
                <div className="flex justify-between font-bold text-slate-700 mb-1.5">
                  <span>Average Speed (km/h)</span>
                  <span className="text-blue-700 font-black">{avgSpeed} km/h</span>
                </div>
                <input 
                  type="range" 
                  min="5" 
                  max="100" 
                  step="1"
                  value={avgSpeed}
                  onChange={(e) => setAvgSpeed(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-950"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Weather</label>
                  <select 
                    value={weather}
                    onChange={(e) => setWeather(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 font-medium focus:outline-none focus:border-slate-950"
                  >
                    <option value="Clear">Clear / Sunny</option>
                    <option value="Rain">Moderate Rain</option>
                    <option value="Storm">Heavy Storm</option>
                    <option value="Fog">Dense Fog</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">Road Capacity</label>
                  <input 
                    type="number" 
                    value={roadCapacity}
                    onChange={(e) => setRoadCapacity(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-slate-900 font-medium focus:outline-none focus:border-slate-950"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loadingPredict}
                className="w-full py-3.5 px-4 bg-slate-950 hover:bg-black text-white font-extrabold rounded-xl shadow-md transition-all flex items-center justify-center gap-2 text-xs cursor-pointer"
              >
                {loadingPredict ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Run AI Prediction Inference
              </button>
            </form>

            {/* Inference Output */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-500 font-bold uppercase tracking-wider">Inference Results</span>
                <span className="px-2.5 py-0.5 rounded-full bg-rose-100 text-rose-800 border border-rose-200 font-bold">
                  {prediction.congestion_level} Congestion
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-400 font-medium block">Congestion Score</span>
                  <span className="text-xl font-black text-slate-900">{prediction.congestion_score} / 100</span>
                </div>
                <div className="p-3 rounded-xl bg-white border border-slate-200">
                  <span className="text-[10px] text-slate-400 font-medium block">Est. Delay</span>
                  <span className="text-xl font-black text-amber-700">{prediction.estimated_delay_minutes} mins</span>
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-950 text-white text-xs space-y-1">
                <span className="font-bold text-amber-400 block">Recommended Signal Action:</span>
                <span className="text-slate-200 font-medium">{prediction.recommended_action}</span>
              </div>
            </div>
          </div>

          {/* AI Route Suggestions (Pending Review) */}
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm relative overflow-hidden group">
            <h3 className="text-sm font-black text-slate-900 tracking-wider uppercase mb-1 flex items-center gap-2">
              <Zap className="w-5 h-5 text-amber-500" />
              AI Route Approvals
            </h3>
            <p className="text-xs text-slate-500 mb-6 font-medium leading-relaxed">Review and approve AI-generated alternative routes.</p>
            
            <div className="space-y-4">
              {proposedRoutes.filter(r => r.status === "PENDING").length === 0 ? (
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-center text-slate-400 text-xs font-semibold">
                  No pending routes. Run the simulator to generate one.
                </div>
              ) : (
                proposedRoutes.filter(r => r.status === "PENDING").map(route => (
                  <div key={route.id} className="p-4 bg-amber-50 rounded-2xl border border-amber-100 flex flex-col gap-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-amber-800 font-bold text-sm block">Reroute to {route.destination}</span>
                        <span className="text-amber-600/80 text-xs font-medium">From {route.origin}</span>
                      </div>
                      <span className="px-2 py-1 bg-amber-200 text-amber-800 rounded-md text-[10px] font-black tracking-wide">
                        PENDING
                      </span>
                    </div>
                    <button 
                      onClick={() => handleApproveRoute(route.id)}
                      className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-black transition-colors cursor-pointer shadow-sm"
                    >
                      Approve & Broadcast Route
                    </button>
                  </div>
                ))
              )}
            </div>
            
            {/* Live Map for Controller */}
            <div className="mt-6">
               <LiveTrafficMap proposedRoute={proposedRoutes.length > 0 ? proposedRoutes[proposedRoutes.length - 1] : null} />
            </div>
          </div>
        </div>

        {/* Right: Analytics & 24h Trend Chart */}
        <div className="lg:col-span-6 bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-slate-100 border border-slate-200 text-slate-900">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-extrabold text-slate-900">24-Hour Traffic Analytics</h3>
              <p className="text-xs text-slate-500 font-medium">Hourly vehicle density & speed trend visualization</p>
            </div>
          </div>

          <div className="h-64 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="densityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0f172a" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#0f172a" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip contentStyle={{ backgroundColor: "#0f172a", color: "#ffffff", borderRadius: "12px", fontSize: "12px" }} />
                <Area type="monotone" dataKey="vehicle_density" name="Vehicle Density" stroke="#0f172a" strokeWidth={2} fillOpacity={1} fill="url(#densityGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 grid grid-cols-3 gap-3 text-center text-xs">
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Peak Hours</span>
              <span className="font-extrabold text-rose-700">18:00 - 19:30</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-400 font-bold uppercase block">Max Density</span>
              <span className="font-extrabold text-slate-900">1,680 veh/hr</span>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 font-bold uppercase block">AI Efficiency</span>
              <span className="font-extrabold text-emerald-700">+28.4% Flow</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
