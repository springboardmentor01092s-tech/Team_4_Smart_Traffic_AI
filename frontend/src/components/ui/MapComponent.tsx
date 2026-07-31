"use client";

import React from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41]
});

export interface RouteProp {
  id: string;
  origin: string;
  destination: string;
  status: string;
}

export default function MapComponent({ proposedRoute }: { proposedRoute?: RouteProp | null }) {
  const center: [number, number] = [12.9716, 77.5946];

  const primaryRouteCoords: [number, number][] = [
    [12.9716, 77.5946],
    [12.9816, 77.5996],
    [12.9916, 77.6046]
  ];
  
  const alternateRouteCoords: [number, number][] = [
    [12.9716, 77.5946],
    [12.9750, 77.6100],
    [12.9916, 77.6046]
  ];

  return (
    <div className="w-full h-[350px] sm:h-[450px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative z-0">
      <MapContainer center={center} zoom={13} scrollWheelZoom={false} className="h-full w-full z-0 relative">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        
        <Polyline positions={primaryRouteCoords} color="#ef4444" weight={6} opacity={0.7} />
        
        {proposedRoute && (
          <Polyline 
            positions={alternateRouteCoords} 
            color={proposedRoute.status === "APPROVED" ? "#10b981" : "#f59e0b"} 
            weight={7} 
            dashArray={proposedRoute.status === "PENDING" ? "10, 10" : undefined}
          />
        )}
        
        <Marker position={primaryRouteCoords[0]} icon={icon}>
          <Popup>Origin Zone</Popup>
        </Marker>
        <Marker position={primaryRouteCoords[2]} icon={icon}>
          <Popup>Destination Zone</Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}
