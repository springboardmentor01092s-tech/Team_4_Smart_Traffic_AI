"use client";

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { GoogleMap, useJsApiLoader, Marker, Polyline, DirectionsRenderer } from '@react-google-maps/api';
import { Navigation } from 'lucide-react';
import LottieLoader from '@/components/ui/LottieLoader';
import LottieError from '@/components/ui/LottieError';

export interface RouteProp {
  id: string;
  origin: string;
  destination: string;
  status: string; // PENDING, APPROVED
}

const mapContainerStyle = {
  width: '100%',
  height: '100%'
};

// Default center: Downtown Central (e.g. Bangalore coordinates or similar)
const defaultCenter = {
  lat: 12.9716,
  lng: 77.5946
};

// Route markers visualization
const fallbackOriginPos = { lat: 12.9988, lng: 77.5921 };
const fallbackDestPos = { lat: 12.9507, lng: 77.5848 };

// Use a static array for libraries to prevent reload warnings
const LIBRARIES: ("places")[] = ["places"];

// Custom SVG Marker for User
const userSvgIcon = `data:image/svg+xml;utf-8, \
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32"> \
    <circle cx="12" cy="12" r="10" fill="%233b82f6" fill-opacity="0.2" /> \
    <circle cx="12" cy="12" r="6" fill="%232563eb" stroke="%23ffffff" stroke-width="2" /> \
  </svg>`;

export default function LiveTrafficMap({ 
  proposedRoute, 
  userLocation,
  directionsResult = null,
  selectedRouteIndex = 0,
  osmRoutes = []
}: { 
  proposedRoute?: RouteProp | null;
  userLocation?: { lat: number; lng: number } | null;
  directionsResult?: google.maps.DirectionsResult | null;
  selectedRouteIndex?: number;
  osmRoutes?: { path: { lat: number; lng: number }[]; color: string; index: number }[];
}) {
  const { isLoaded, loadError } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
    libraries: LIBRARIES
  });

  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [internalDirections, setInternalDirections] = useState<google.maps.DirectionsResult | null>(null);
  const skipGoogleDirections = useRef(false);

  const originStr = proposedRoute ? proposedRoute.origin : "Bangalore Palace, Bangalore";
  const destinationStr = proposedRoute ? proposedRoute.destination : "Lalbagh Botanical Garden, Bangalore";

  // Avoid calling Google DirectionsService internally without billing enabled; rely on OSRM polylines and external directions.

  // Pan to user location when received
  useEffect(() => {
    if (map && userLocation && !directionsResult && !internalDirections && (!osmRoutes || osmRoutes.length === 0)) {
      map.panTo(userLocation);
    }
  }, [map, userLocation, directionsResult, internalDirections, osmRoutes]);

  // Adjust bounds for OSRM fallback real-time road paths
  useEffect(() => {
    if (map && osmRoutes && osmRoutes.length > 0 && window.google && window.google.maps) {
      const selected = osmRoutes[selectedRouteIndex] || osmRoutes[0];
      if (selected && selected.path && selected.path.length > 0) {
        const bounds = new window.google.maps.LatLngBounds();
        selected.path.forEach((p: { lat: number; lng: number }) => bounds.extend(p));
        map.fitBounds(bounds);
      }
    }
  }, [map, osmRoutes, selectedRouteIndex]);

  const handleRecenter = () => {
    if (map && userLocation) {
      map.panTo(userLocation);
      map.setZoom(14);
    }
  };

  const onLoad = useCallback(function callback(mapInstance: google.maps.Map) {
    setMap(mapInstance);
  }, []);

  const onUnmount = useCallback(function callback() {
    setMap(null);
  }, []);

  const routeColor = proposedRoute?.status === "APPROVED" ? "#10b981" : proposedRoute?.status === "PENDING" ? "#f59e0b" : "#ef4444";

  if (loadError) return (
    <div className="w-full h-[350px] sm:h-[450px] rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center p-4">
      <LottieError 
        title="Failed to Load Map Engine" 
        text="Unable to initialize Google Maps interface. Please check telemetry connection or network permissions."
        showRetry={true} 
        size="md" 
      />
    </div>
  );

  if (!isLoaded) return (
    <div className="w-full h-[350px] sm:h-[450px] rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center">
      <LottieLoader text="Loading real-time Google Maps SDK..." size="md" />
    </div>
  );

  const effectiveDirections = directionsResult || internalDirections;

  return (
    <div className="w-full h-[350px] sm:h-[450px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative z-0">
      {userLocation && (
        <button
          type="button"
          onClick={handleRecenter}
          className="absolute bottom-4 right-4 z-10 bg-white/90 backdrop-blur-md hover:bg-white text-slate-800 text-xs font-bold px-3 py-2 rounded-xl shadow-md border border-slate-200 flex items-center gap-2 transition-all cursor-pointer hover:shadow-lg active:scale-95"
          title="Recenter map to your live position"
        >
          <Navigation className="w-3.5 h-3.5 text-blue-600" />
          <span>Recenter My Location</span>
        </button>
      )}

      <GoogleMap
        mapContainerStyle={mapContainerStyle}
        center={userLocation || defaultCenter}
        zoom={13}
        onLoad={onLoad}
        onUnmount={onUnmount}
        options={{
          disableDefaultUI: false,
          zoomControl: true,
          styles: [
            {
              featureType: "poi",
              elementType: "labels",
              stylers: [{ visibility: "off" }]
            }
          ]
        }}
      >
        {effectiveDirections && effectiveDirections.routes ? (
          effectiveDirections.routes.map((_, idx) => (
            <DirectionsRenderer
              key={idx}
              directions={effectiveDirections}
              routeIndex={idx}
              options={{
                suppressMarkers: idx !== selectedRouteIndex,
                preserveViewport: idx !== selectedRouteIndex,
                polylineOptions: {
                  strokeColor: idx === selectedRouteIndex ? (proposedRoute?.status === "PENDING" ? "#f59e0b" : "#10b981") : "#94a3b8",
                  strokeWeight: idx === selectedRouteIndex ? 6 : 4,
                  strokeOpacity: idx === selectedRouteIndex ? 0.9 : 0.4,
                  zIndex: idx === selectedRouteIndex ? 50 : 10,
                }
              }}
            />
          ))
        ) : osmRoutes && osmRoutes.length > 0 ? (
          <>
            {(() => {
              const activeRt = osmRoutes[selectedRouteIndex] || osmRoutes[0];
              if (!activeRt) return null;
              return (
                <Polyline
                  key={activeRt.index}
                  path={activeRt.path}
                  options={{
                    strokeColor: activeRt.color || "#10b981",
                    strokeWeight: 7,
                    strokeOpacity: 0.95,
                    zIndex: 100,
                  }}
                />
              );
            })()}
            {osmRoutes[selectedRouteIndex]?.path?.[0] && !userLocation && (
              <Marker position={osmRoutes[selectedRouteIndex].path[0]} title={`Origin: ${originStr}`} />
            )}
            {osmRoutes[selectedRouteIndex]?.path?.[osmRoutes[selectedRouteIndex].path.length - 1] && (
              <Marker position={osmRoutes[selectedRouteIndex].path[osmRoutes[selectedRouteIndex].path.length - 1]} title={`Destination: ${destinationStr}`} />
            )}
          </>
        ) : (
          <>
            <Marker position={fallbackOriginPos} title={`Origin: ${originStr}`} />
            <Marker position={fallbackDestPos} title={`Destination: ${destinationStr}`} />
            <Polyline 
              path={[fallbackOriginPos, fallbackDestPos]}
              options={{
                strokeColor: routeColor,
                strokeWeight: 5,
                strokeOpacity: 0.7,
                geodesic: true
              }}
            />
          </>
        )}

        {userLocation && window.google && (
          <Marker 
            position={userLocation} 
            icon={{
              url: userSvgIcon,
              anchor: new window.google.maps.Point(16, 16)
            }}
            title="Your Real-Time Location"
          />
        )}
      </GoogleMap>
    </div>
  );
}


