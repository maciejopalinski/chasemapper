#!/bin/sh

LINK="https://download.geofabrik.de/europe/poland/dolnoslaskie-latest.osm.pbf"
FILENAME="dolnoslaskie-latest.osm.pbf"

mkdir -p ./osm-tile-server/

wget "$LINK" -O "./osm-tile-server/$FILENAME"

docker run --rm -t -v "$(pwd)/osm-tile-server/$FILENAME:/data/region.osm.pbf" -v "$(pwd)/osm-tile-server/database/:/data/database/" -e THREADS=$(nproc) overv/openstreetmap-tile-server import