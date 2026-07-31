"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { GoogleMap, useJsApiLoader, DirectionsRenderer, Marker } from '@react-google-maps/api';

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
  userLocation 
}: { 
  proposedRoute?: RouteProp | null;
  userLocation?: { lat: number; lng: number } | null;
}) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
    libraries: LIBRARIES
  });

  const [map, setMap] = useState<google.maps.Map | null>(null);
  const [directionsResponse, setDirectionsResponse] = useState<google.maps.DirectionsResult | null>(null);
  
  // Hardcoded for MVP since route optimization currently mocks endpoints
  const originStr = proposedRoute ? proposedRoute.origin : "Bangalore Palace, Bangalore";
  const destinationStr = proposedRoute ? proposedRoute.destination : "Lalbagh Botanical Garden, Bangalore";

  const calculateRoute = useCallback(async () => {
    if (!isLoaded) return;
    
    // eslint-disable-next-line no-undef
    const directionsService = new google.maps.DirectionsService();
    try {
      const results = await directionsService.route({
        origin: originStr,
        destination: destinationStr,
        // eslint-disable-next-line no-undef
        travelMode: google.maps.TravelMode.DRIVING,
        provideRouteAlternatives: true
      });
      setDirectionsResponse(results);
    } catch (error) {
      console.error("Error fetching directions", error);
    }
  }, [isLoaded, originStr, destinationStr]);

  useEffect(() => {
    if (isLoaded) {
      calculateRoute();
    }
  }, [isLoaded, calculateRoute]);

  const onLoad = useCallback(function callback(mapInstance: google.maps.Map) {
    setMap(mapInstance);
  }, []);

  const onUnmount = useCallback(function callback() {
    setMap(null);
  }, []);

  const routeColor = proposedRoute?.status === "APPROVED" ? "#10b981" : proposedRoute?.status === "PENDING" ? "#f59e0b" : "#ef4444";

  if (!isLoaded) return (
    <div className="w-full h-[350px] sm:h-[450px] rounded-2xl bg-slate-100 animate-pulse border border-slate-200 flex items-center justify-center text-slate-400 font-semibold text-sm">
      Loading Google Maps...
    </div>
  );

  return (
    <div className="w-full h-[350px] sm:h-[450px] rounded-2xl overflow-hidden border border-slate-200 shadow-sm relative z-0">
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
        {directionsResponse && (
          <DirectionsRenderer 
            directions={directionsResponse}
            options={{
              polylineOptions: {
                strokeColor: routeColor,
                strokeWeight: 6,
                strokeOpacity: 0.8
              },
              suppressMarkers: false // default markers for origin/dest
            }}
          />
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
