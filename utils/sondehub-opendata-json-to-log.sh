jq -c 'map({
  sats: .sats,
  log_time: .time_received,
  temp: -1,
  lon: .lon,
  callsign: .serial,
  time: .datetime,
  lat: .lat,
  alt: .alt,
  log_type: "BALLOON TELEMETRY"
})[]' "$1"