import {
    MapContainer,
    Marker,
    Popup,
    SVGOverlay,
    TileLayer,
    useMap,
} from "react-leaflet";
import "leaflet-rotate";

import NavigationIcon from "./assets/navigation.svg";
import { useGeolocated } from "react-geolocated";
import { Icon, icon, SVG } from "leaflet";
import { useMemo } from "react";

function BearingButton() {
    const map = useMap();

    return (
        <button
            style={{
                display: "block",
                position: "absolute",
                top: "20px",
                left: "100px",
                zIndex: 1000,
            }}
            onClick={() => {
                map.setBearing(map.getBearing() + 10);

                console.log(map.getBearing());
            }}
        >
            Rotate
        </button>
    );
}

function CarMarker({ coords }: { coords: GeolocationCoordinates }) {
    const map = useMap();

    map.flyTo([coords.latitude, coords.longitude], map.getZoom(), {
        animate: true,
    });

    useMemo(() => {
        map.setBearing(coords.heading || 0);
    }, [map, coords.heading]);

    return (
        <Marker
            position={[coords.latitude, coords.longitude]}
            rotation={coords.heading || undefined}
            icon={new Icon({ iconUrl: NavigationIcon, iconSize: [50, 50] })}
        />
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

            <BearingButton />

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
