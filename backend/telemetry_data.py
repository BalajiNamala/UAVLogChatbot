from pymavlink import mavutil
import datetime
import json
import sys

file_path = sys.argv[1] if len(sys.argv) > 1 else "vtol.tlog"
mav = mavutil.mavlink_connection(file_path)

max_altitude = 0
flight_modes = set()
gps_loss_times = []
battery_low = False
start_time = None
end_time = None

while True:
    msg = mav.recv_match(type=['GLOBAL_POSITION_INT', 'BATTERY_STATUS', 'HEARTBEAT', 'GPS_RAW_INT'], blocking=False)
    if msg is None:
        break

    timestamp = datetime.datetime.utcfromtimestamp(msg._timestamp)
    if start_time is None:
        start_time = timestamp
    end_time = timestamp

    if msg.get_type() == 'GLOBAL_POSITION_INT':
        altitude = msg.relative_alt / 1000.0
        max_altitude = max(max_altitude, altitude)

    if msg.get_type() == 'BATTERY_STATUS':
        if msg.battery_remaining is not None and msg.battery_remaining < 20:
            battery_low = True

    if msg.get_type() == 'HEARTBEAT':
        try:
            mode_mapping = mav.mode_mapping()[msg.type]
            mode = mode_mapping.get(msg.custom_mode, "UNKNOWN")
            flight_modes.add(mode)
        except Exception:
            flight_modes.add("UNKNOWN")

    if msg.get_type() == 'GPS_RAW_INT' and msg.fix_type < 3:
        gps_loss_times.append(timestamp.isoformat())

telemetry = {
    "takeoffTime": start_time.isoformat() if start_time else None,
    "maxAltitude": round(max_altitude, 2),
    "flightModes": sorted(flight_modes),
    "gpsLossTimes": gps_loss_times[:5],
    "batteryLow": battery_low,
    "flightDurationSec": int((end_time - start_time).total_seconds()) if start_time and end_time else None
}

print(json.dumps(telemetry, indent=2))
