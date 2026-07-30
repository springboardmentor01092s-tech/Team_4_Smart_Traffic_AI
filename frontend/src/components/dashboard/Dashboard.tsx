"use client";

import React, { useState } from "react";
import { 
  Activity, 
  AlertTriangle, 
  Car, 
  CheckCircle, 
  Clock, 
  Compass, 
  Cpu, 
  LogOut,
  Navigation, 
  RefreshCw, 
  ShieldAlert, 
  TrendingUp, 
  User,
  Zap 
} from "lucide-react";

import CityFlowXLogo from "@/components/ui/CityFlowXLogo";

interface DashboardProps {
  user?: { role: string; email: string };
  onLogout?: () => void;
}

export default function Dashboard({ user, onLogout }: DashboardProps) {
  const [vehicleCount, setVehicleCount] = useState<number>(780);
  const [avgSpeed, setAvgSpeed] = useState<number>(34.5);
  const [weather, setWeather] = useState<string>("Clear");
  const [isPeakHour, setIsPeakHour] = useState<boolean>(true);
  const [roadCapacity, setRoadCapacity] = useState<number>(1000);
  
  const [prediction, setPrediction] = useState<{
    congestion_level: string;
    congestion_score: number;
    estimated_delay_minutes: number;
    recommended_action: string;
  }>({
    congestion_level: "Moderate",
    congestion_score: 58.4,
    estimated_delay_minutes: 14.6,
    recommended_action: "Extend green wave timing on main corridor by +15s."
  });

  const [loading, setLoading] = useState(false);

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/v1/traffic/predict", {
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
      } else {
        const ratio = vehicleCount / Math.max(roadCapacity, 1);
        const score = Math.min(100, Math.max(0, ratio * 60 + (60 - avgSpeed) * 0.8 + (isPeakHour ? 15 : 0)));
        const level = score < 35 ? "Low" : score < 70 ? "Moderate" : "High";
        const delay = Math.round(score * 0.25 * 10) / 10;
        setPrediction({
          congestion_level: level,
          congestion_score: Math.round(score * 10) / 10,
          estimated_delay_minutes: delay,
          recommended_action: level === "High" 
            ? "Reroute incoming traffic & trigger dynamic green wave priority." 
            : level === "Moderate" 
            ? "Extend main corridor green light signal by +15 seconds." 
            : "Standard automated traffic signal timing."
        });
      }
    } catch {
      const ratio = vehicleCount / Math.max(roadCapacity, 1);
      const score = Math.min(100, Math.max(0, ratio * 60 + (60 - avgSpeed) * 0.8 + (isPeakHour ? 15 : 0)));
      const level = score < 35 ? "Low" : score < 70 ? "Moderate" : "High";
      setPrediction({
        congestion_level: level,
        congestion_score: Math.round(score * 10) / 10,
        estimated_delay_minutes: Math.round(score * 0.25 * 10) / 10,
        recommended_action: level === "High" ? "Reroute traffic to arterial bypass" : "Maintain normal green wave timing"
      });
    } finally {
      setLoading(false);
    }
  };

  const getBadgeColor = (level: string) => {
    switch (level) {
      case "Low":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "Moderate":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "High":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      default:
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 md:p-10">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between border-b border-slate-800 pb-6 mb-8 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-black tracking-tight text-white">
            CityFlow<span className="text-amber-400">X</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 font-medium">Smart Urban Traffic Control</p>
        </div>
        <div className="flex items-center gap-3">
          {user && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 text-xs">
              <User className="w-3.5 h-3.5 text-amber-400" />
              <span className="font-semibold">{user.role}</span>
              <span className="text-slate-500">({user.email})</span>
            </div>
          )}
          <span className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-semibold border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            System Online
          </span>
          {onLogout && (
            <button 
              onClick={onLogout}
              className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 hover:border-rose-500/40 text-slate-300 hover:text-rose-400 transition-all flex items-center gap-1.5 text-xs font-medium"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Sign Out</span>
            </button>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto space-y-8">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Active Junctions</span>
              <Navigation className="w-5 h-5 text-blue-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-white">42</div>
            <div className="mt-1 text-xs text-slate-400 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
              100% Sensors Online
            </div>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Vehicles Monitored</span>
              <Car className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-white">12,850</div>
            <div className="mt-1 text-xs text-emerald-400 flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" />
              +4.2% vs last hour
            </div>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">Average Corridor Speed</span>
              <Compass className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-white">{avgSpeed} <span className="text-sm font-normal text-slate-400">km/h</span></div>
            <div className="mt-1 text-xs text-slate-400">Optimal flow: 50 km/h</div>
          </div>

          <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 backdrop-blur-md">
            <div className="flex items-center justify-between">
              <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">System Latency</span>
              <Cpu className="w-5 h-5 text-purple-400" />
            </div>
            <div className="mt-3 text-3xl font-bold text-white">12 <span className="text-sm font-normal text-slate-400">ms</span></div>
            <div className="mt-1 text-xs text-purple-400">Ultra low latency</div>
          </div>
        </div>

        {/* Interactive ML Simulator & Prediction Results */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Controls Form */}
          <div className="lg:col-span-6 bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">AI Congestion Simulator</h2>
                <p className="text-xs text-slate-400">Tune real-time parameters to run neural inference</p>
              </div>
            </div>

            <form onSubmit={handlePredict} className="space-y-5">
              <div>
                <div className="flex justify-between text-xs font-medium text-slate-300 mb-2">
                  <span>Vehicle Density (Vehicles / hr)</span>
                  <span className="text-blue-400 font-bold">{vehicleCount}</span>
                </div>
                <input 
                  type="range" 
                  min="100" 
                  max="2000" 
                  step="20"
                  value={vehicleCount}
                  onChange={(e) => setVehicleCount(Number(e.target.value))}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-medium text-slate-300 mb-2">
                  <span>Average Speed (km/h)</span>
                  <span className="text-cyan-400 font-bold">{avgSpeed} km/h</span>
                </div>
                <input 
                  type="range" 
                  min="5" 
                  max="100" 
                  step="1"
                  value={avgSpeed}
                  onChange={(e) => setAvgSpeed(Number(e.target.value))}
                  className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-2">Weather Condition</label>
                  <select 
                    value={weather}
                    onChange={(e) => setWeather(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                  >
                    <option value="Clear">Clear / Sunny</option>
                    <option value="Rain">Moderate Rain</option>
                    <option value="Storm">Heavy Storm</option>
                    <option value="Fog">Dense Fog</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-2">Road Capacity</label>
                  <input 
                    type="number" 
                    value={roadCapacity}
                    onChange={(e) => setRoadCapacity(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-xl">
                <span className="text-xs font-medium text-slate-300">Peak Rush Hour Mode</span>
                <button
                  type="button"
                  onClick={() => setIsPeakHour(!isPeakHour)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isPeakHour ? 'bg-blue-600' : 'bg-slate-800'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isPeakHour ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3.5 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 transition-all flex items-center justify-center gap-2"
              >
                {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
                Run Traffic AI Prediction
              </button>
            </form>
          </div>

          {/* Inference Output Card */}
          <div className="lg:col-span-6 flex flex-col justify-between bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-xl">
            <div>
              <div className="flex items-center justify-between mb-6">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Real-time Inference Output</span>
                <span className={`px-3 py-1 rounded-full border text-xs font-bold ${getBadgeColor(prediction.congestion_level)}`}>
                  {prediction.congestion_level} Congestion
                </span>
              </div>

              {/* Congestion Gauge Meter */}
              <div className="space-y-4 mb-8">
                <div className="flex justify-between items-end">
                  <span className="text-sm text-slate-300">Congestion Index</span>
                  <span className="text-3xl font-extrabold text-white">{prediction.congestion_score} <span className="text-base font-normal text-slate-400">/ 100</span></span>
                </div>
                <div className="w-full h-3 bg-slate-950 rounded-full overflow-hidden p-0.5 border border-slate-800">
                  <div 
                    className={`h-full rounded-full transition-all duration-700 ${
                      prediction.congestion_score > 70 
                        ? 'bg-gradient-to-r from-amber-500 to-rose-500' 
                        : prediction.congestion_score > 35 
                        ? 'bg-gradient-to-r from-blue-500 to-amber-500' 
                        : 'bg-gradient-to-r from-emerald-500 to-blue-500'
                    }`}
                    style={{ width: `${Math.min(100, prediction.congestion_score)}%` }}
                  />
                </div>
              </div>

              {/* Delay & Action Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-2xl">
                  <div className="flex items-center gap-2 text-slate-400 text-xs font-medium mb-1">
                    <Clock className="w-4 h-4 text-amber-400" />
                    Est. Commute Delay
                  </div>
                  <div className="text-2xl font-bold text-white">{prediction.estimated_delay_minutes} <span className="text-sm text-slate-400">mins</span></div>
                </div>

                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-2xl">
                  <div className="flex items-center gap-2 text-slate-400 text-xs font-medium mb-1">
                    <ShieldAlert className="w-4 h-4 text-blue-400" />
                    Safety Factor
                  </div>
                  <div className="text-2xl font-bold text-emerald-400">98.5%</div>
                </div>
              </div>

              <div className="p-5 bg-gradient-to-br from-slate-950 to-slate-900 border border-slate-800 rounded-2xl">
                <div className="flex items-center gap-2 text-xs font-bold text-blue-400 uppercase tracking-wider mb-2">
                  <AlertTriangle className="w-4 h-4" />
                  Recommended Autonomous Action
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-medium">
                  {prediction.recommended_action}
                </p>
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
              <span>Model Artifact: XGBoost / Random Forest</span>
              <span>Updated: Just now</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
