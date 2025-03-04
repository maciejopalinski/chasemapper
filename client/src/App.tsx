import { MapContainer, Marker, TileLayer, useMap } from "react-leaflet";
import Control from "react-leaflet-custom-control";
import "leaflet-rotate";

import NavigationIcon from "./assets/navigation.svg";
import { useGeolocated } from "react-geolocated";
import { Icon } from "leaflet";
import { useCallback, useMemo } from "react";

function CarMarker({ coords }: { coords: GeolocationCoordinates }) {
    const map = useMap();

    map.flyTo([coords.latitude, coords.longitude], map.getZoom(), {
        animate: true,
    });

    useMemo(() => {
        map.setBearing(coords.heading || 0);
    }, [map, coords.heading]);

    return (
        <div className="car-marker">
            <Marker
                position={[coords.latitude, coords.longitude]}
                rotation={coords.heading || undefined}
                icon={new Icon({ iconUrl: NavigationIcon, iconSize: [50, 50] })}
            />
        </div>
    );
}

function CustomControl() {
    // ! TODO: react-leaflet-custom…ol.js?v=74338880:72 Uncaught Error: No context provided: useLeafletContext() can only be used in a descendant of <MapContainer>
    // why? it is inside MapContainer...
    const map = useMap();
    const rotate = useCallback(() => {
        map.setBearing(map.getBearing() + 10);

        console.log(map.getBearing());
    }, [map]);

    return (
        <Control position="topright">
            <button>location</button>

            <button
                style={{
                    display: "block",
                    position: "absolute",
                    top: "20px",
                    left: "100px",
                    zIndex: 1000,
                }}
                onClick={rotate}
            >
                Rotate
            </button>
        </Control>
    );
}

function App() {
    const { coords } = useGeolocated({
        positionOptions: { enableHighAccuracy: true },
        watchPosition: true,
        onSuccess: (pos) => console.log(pos),
    });

    return (
        <MapContainer
            center={coords ? [coords.latitude, coords.longitude] : [51, 17]}
            zoom={13}
            scrollWheelZoom={false}
            style={{ height: "100vh", width: "100%" }}
            rotate={true}
            touchRotate={false}
            bearing={0}
            attributionControl={false}
            rotateControl={true}
            zoomControl={true}
        >
            <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <CustomControl />

            {/* <SVGOverlay
                attributes={{ stroke: "red" }}
                bounds={[
                    [51.49, -0.1],
                    [51.5, -0.08],
                ]}
            >
                <rect x="0" y="0" width="100%" height="100%" fill="blue" />
                <circle r="5" cx="10" cy="10" fill="red" />
                <text x="50%" y="50%" stroke="white">
                    text
                </text>
            </SVGOverlay> */}

            {coords && <CarMarker coords={coords} />}
        </MapContainer>
    );
}

export default App;
