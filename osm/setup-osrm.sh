#!/bin/sh

LINK="https://download.geofabrik.de/europe/poland-latest.osm.pbf"
FILENAME="poland-latest.osm.pbf"

mkdir -p ./osrm/

wget "$LINK" -O "./osrm/$FILENAME"

docker run --rm -t -v "$(pwd)/osrm/:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/$FILENAME || echo "osrm-extract failed"

docker run --rm -t -v "$(pwd)/osrm/:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/$FILENAME || echo "osrm-partition failed"

docker run --rm -t -v "$(pwd)/osrm/:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/$FILENAME || echo "osrm-customize failed"