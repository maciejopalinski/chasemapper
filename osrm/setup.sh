#!/bin/sh

mkdir -p ./data/

wget https://download.geofabrik.de/europe/poland-latest.osm.pbf

docker run --rm -t -v "./data:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/poland-latest.osm.pbf || echo "osrm-extract failed"

docker run --rm -t -v "./data:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/berlin-latest.osrm || echo "osrm-partition failed"

docker run --rm -t -v "./data:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/berlin-latest.osrm || echo "osrm-customize failed"