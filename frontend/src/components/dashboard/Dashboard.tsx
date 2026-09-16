"use client";

import React from "react";
import { 
  Car, 
  CheckCircle2, 
  Compass, 
  Cpu, 
  LogOut, 
  Navigation, 
  ShieldAlert, 
  User,
  Menu,
  Bell,
  Trash2
} from "lucide-react";

import CivilianDashboard from "./CivilianDashboard";
import ControllerDashboard from "./ControllerDashboard";

import { getApiUrl } from "@/lib/api";
import ToastAlert from "@/components/ui/ToastAlert";

interface DashboardProps {
  user?: { role: string; email: string; name?: string };
  onLogout?: () => void;
}

export default function Dashboard({ user, onLogout }: DashboardProps) {
  const isController = user?.role?.toLowerCase().includes("controller");
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = React.useState(false);
  const [showNotifications, setShowNotifications] = React.useState(false);
  const [notifications, setNotifications] = React.useState<any[]>([]);
  const [activeToast, setActiveToast] = React.useState<{ type: "success" | "error" | "warning"; message: string } | null>(null);
  const lastNotificationId = React.useRef<number>(0);

  const fetchNotifications = React.useCallback(async () => {
    try {
      const res = await fetch(getApiUrl("traffic/notifications"));
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
        
        if (data.length > 0) {
          const latest = data[0];
          if (latest.id > lastNotificationId.current) {
            if (lastNotificationId.current !== 0) {
              const toastType = latest.type === "danger" ? "error" : latest.type === "warning" ? "warning" : "success";
              setActiveToast({
                type: toastType,
                message: latest.text
              });
            }
            lastNotificationId.current = latest.id;
          }
        }
      }
    } catch (e) {
      console.warn("Notifications fetch error:", e);
    }
  }, []);

  React.useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 4000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const clearNotifications = async () => {
    try {
      const res = await fetch(getApiUrl("traffic/notifications/clear"), { method: "POST" });
      if (res.ok) {
        setNotifications([]);
      }
    } catch {}
  };

  // Format display username (e.g., "Nagul", "Arunprasath", or "Head Traffic Controller")
  const getDisplayUsername = () => {
    if (user?.name && user.name.trim() && user.name.trim() !== user.email && !user.name.toLowerCase().includes("google.user")) {
      return user.name.trim();
    }
    if (user?.email && !user.email.toLowerCase().includes("google.user")) {
      const prefix = user.email.split("@")[0];
      if (prefix.toLowerCase() === "trafficcontroller") return "Head Traffic Controller";
      return prefix.charAt(0).toUpperCase() + prefix.slice(1);
    }
    return isController ? "Head Traffic Controller" : "Nagul";
  };

  const username = getDisplayUsername();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans p-3 sm:p-5 md:p-8 select-none w-full max-w-full">
      {activeToast && (
        <ToastAlert 
          type={activeToast.type} 
          message={activeToast.message} 
          onClose={() => setActiveToast(null)} 
        />
      )}

      
      {/* Top Header matching Login Page Aesthetics */}
      <header className="w-full max-w-full flex items-start md:items-center justify-between border-b border-slate-200 pb-6 mb-8 gap-3">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl md:text-3xl font-black tracking-tight text-slate-950">
                CityFlow<span className="text-amber-500">X</span>
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200 text-[10px] font-black uppercase hidden sm:inline-block">
                {isController ? "Traffic Controller Command" : "Civilian Commuter System"}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-medium">Smart Urban Traffic Management Platform</p>
          </div>
        </div>

        {/* User Info Badge & Sign Out */}
        <div className="flex items-center gap-3 justify-end relative">
          
          {/* Mobile Layout */}
          <div className="sm:hidden flex items-center justify-end gap-2">

             <button onClick={() => setShowNotifications(!showNotifications)} className="relative p-2 border border-slate-200 rounded-xl bg-white hover:bg-slate-50 cursor-pointer">
               <Bell className="w-5 h-5 text-slate-700" />
               {notifications.length > 0 && (
                 <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full animate-pulse border-2 border-white" />
               )}
             </button>

             <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="p-2 border border-slate-200 rounded-xl bg-white hover:bg-slate-50 cursor-pointer">
               <Menu className="w-5 h-5 text-slate-700" />
             </button>
          </div>

          {/* Desktop User Info & Sign Out */}
          <div className="hidden sm:flex items-center gap-3 relative">
            
            <button 
              onClick={() => setShowNotifications(!showNotifications)} 
              className="relative p-2.5 rounded-2xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 transition-colors cursor-pointer"
            >
              <Bell className="w-4 h-4 text-slate-700" />
              {notifications.length > 0 && (
                 <span className="absolute top-1.5 right-2 w-2 h-2 bg-rose-500 rounded-full animate-pulse border-2 border-white" />
              )}
            </button>

            <div className="flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-white border border-slate-200 text-xs shadow-sm font-medium">
              {isController ? (
                <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
              ) : (
                <User className="w-4 h-4 text-emerald-600 shrink-0" />
              )}
              <span className="truncate max-w-[150px] font-bold">{username}</span>
            </div>
            <button 
              onClick={() => setShowLogoutConfirm(true)}
              className="p-2.5 rounded-2xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 transition-colors cursor-pointer group"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4 group-hover:text-rose-600 transition-colors" />
            </button>
          </div>

          {/* Notifications Dropdown */}
          {showNotifications && (
            <div className="absolute top-12 sm:top-14 right-12 sm:right-0 w-64 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 p-3 flex flex-col gap-2 origin-top-right animate-in fade-in zoom-in-95 duration-200">
              <div className="flex justify-between items-center px-1 pb-2 border-b border-slate-100">
                <span className="text-xs font-black text-slate-800">Notifications</span>
                {notifications.length > 0 && (
                  <button onClick={clearNotifications} className="text-[10px] font-bold text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors cursor-pointer">
                    <Trash2 className="w-3 h-3" /> Clear
                  </button>
                )}
              </div>
              <div className="max-h-64 overflow-y-auto space-y-2 pr-1">
                {notifications.length === 0 ? (
                  <div className="text-center text-xs text-slate-400 py-4 font-medium">No new notifications</div>
                ) : (
                  notifications.map(n => (
                    <div key={n.id} className="p-2.5 bg-slate-50 rounded-xl border border-slate-100 flex flex-col gap-1 text-left">
                      <span className="text-xs font-semibold text-slate-700 leading-tight">{n.text}</span>
                      <span className="text-[9px] font-bold text-slate-400">{n.time}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* Mobile Dropdown Menu */}
          {mobileMenuOpen && (
            <div className="absolute top-12 right-0 w-48 bg-white border border-slate-200 rounded-2xl shadow-xl z-50 p-2 sm:hidden flex flex-col gap-2">
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 border border-slate-100 text-xs shadow-sm font-medium">
                {isController ? (
                  <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
                ) : (
                  <User className="w-4 h-4 text-emerald-600 shrink-0" />
                )}
                <span className="truncate font-bold text-slate-800">{username}</span>
              </div>
              <div className="h-[1px] bg-slate-100 w-full" />
              <button onClick={() => setShowLogoutConfirm(true)} className="flex items-center gap-2 w-full px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 rounded-xl text-left cursor-pointer">
                <LogOut className="w-4 h-4" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 shadow-2xl max-w-sm w-full animate-in zoom-in-95 duration-200 space-y-6">
            <div className="flex flex-col items-center text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-600 mb-2">
                <LogOut className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-black text-slate-900">Sign Out</h3>
              <p className="text-sm text-slate-500 font-medium">Are you sure you want to sign out of your account?</p>
            </div>
            
            <div className="flex items-center gap-3 w-full pt-2">
              <button 
                onClick={() => setShowLogoutConfirm(false)}
                className="flex-1 py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl transition-colors cursor-pointer text-sm"
              >
                Cancel
              </button>
              <button 
                onClick={() => {
                  setShowLogoutConfirm(false);
                  if (onLogout) onLogout();
                }}
                className="flex-1 py-3 px-4 bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-xl shadow-lg shadow-rose-600/20 transition-all cursor-pointer text-sm"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Full-Width Container */}
      <main className="w-full max-w-full space-y-8">
        
        {/* Real-time System Overview Banner */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Active Intersections</span>
              <Navigation className="w-4 h-4 text-slate-700" />
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-black text-slate-950">42</div>
            <div className="mt-1 text-[11px] text-emerald-600 font-bold flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3" /> 100% Operational
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Vehicles Monitored</span>
              <Car className="w-4 h-4 text-slate-700" />
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-black text-slate-950">12,850</div>
            <div className="mt-1 text-[11px] text-blue-600 font-bold">Live AI Vision</div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Avg Flow Speed</span>
              <Compass className="w-4 h-4 text-slate-700" />
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-black text-slate-950">34.5 <span className="text-xs font-normal text-slate-500">km/h</span></div>
            <div className="mt-1 text-[11px] text-slate-500 font-medium">Optimal City Flow</div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-4 sm:p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>System Latency</span>
              <Cpu className="w-4 h-4 text-slate-700" />
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-black text-slate-950">12 <span className="text-xs font-normal text-slate-500">ms</span></div>
            <div className="mt-1 text-[11px] text-purple-700 font-bold">Ultra Low Latency</div>
          </div>
        </div>

        {/* Dedicated Role-Based Dashboard View */}
        {isController ? (
          <ControllerDashboard />
        ) : (
          <CivilianDashboard username={username} />
        )}

      </main>
    </div>
  );
}
