import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import socket
from threading import Thread
from datetime import datetime
import time
import numpy as np
from itertools import cycle
from gpiozero import LED, Button
# GPIO Setup
red_led = LED(17)
green_led = LED(27)
white_led = LED(22)
yellow_led = LED(23)
button = Button(24, pull_up=True)

# Data Storage
device_master_time = {}
sensor_data = []
timestamps = []
device_colors = {}  # Maps device IPs to colors
master_change_points = []  # Records when the master changes
color_cycle = cycle(["blue", "green", "red", "orange", "purple", "cyan", "magenta"])
current_master = None
last_master_update = time.time()

# LED Color Mapping for Master Devices
led_mapping = {
    "master_1": red_led,
    "master_2": green_led,
    "master_3": white_led
}
# UDP Setup
UDP_IP = "0.0.0.0"
UDP_PORT = 4210
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

# Socket Listener in a Separate Thread
def socket_listener():
    global current_master, last_master_update, master_change_points, device_colors
    while True:
        data, addr = sock.recvfrom(1024)
        print(f"Raw data received: {data} from {addr}")

        try:
            light_reading = int(data.decode().strip())
            ip = addr[0]
            timestamp = time.strftime("%H:%M:%S")

            # Update sensor data
            sensor_data.append(light_reading)
            timestamps.append(timestamp)

            # Update current master
            if ip != current_master:
                if current_master is not None:
                    elapsed_time = time.time() - last_master_update
                    if current_master not in device_master_time:
                        device_master_time[current_master] = 0
                    device_master_time[current_master] += elapsed_time
                current_master = ip
                last_master_update = time.time()
                master_change_points.append(len(sensor_data) - 1)

                # Ensure current master has an entry in device_master_time
                if current_master not in device_master_time:
                    device_master_time[current_master] = 0
                # Update LED based on current master (using dynamic color mapping)
                if current_master not in device_colors:
                    device_colors[current_master] = next(color_cycle)

                # Reset all LEDs before turning on the LED for the current master
                for led in led_mapping.values():
                    led.off()

                # Turn on LED for the current master
                led_color = device_colors[current_master]
                if led_color == "blue":
                    led_mapping["master_1"].on()
                elif led_color == "green":
                    led_mapping["master_2"].on()
                elif led_color == "red":
                    led_mapping["master_3"].on()

            # Initialize master history if new
            if ip not in device_master_time:
                device_master_time[ip] = 0                                                                                                            

        except ValueError:
            print(f"Malformed data: {data}")
            continue

# Plot Updates
def update_graph(frame):
    global timestamps, sensor_data, device_master_time, device_colors, current_master, last_master_update, master_change_points

    ax1.clear()
    ax2.clear()
    # Update Master Duration Accurately
    if current_master:
        elapsed_time = time.time() - last_master_update
        if current_master not in device_master_time:
            device_master_time[current_master] = 0
        device_master_time[current_master] += elapsed_time
        last_master_update = time.time()

    # Plot the sensor data continuously
    if timestamps and sensor_data:
        # Loop through the sensor data and change colors based on the master change points
        for i in range(1, len(sensor_data)):
            start_idx = i - 1
            end_idx = i

            # Determine the color for the current segment
            if len(master_change_points) > 0 and start_idx >= master_change_points[0]:
                # New master change point, update color
                master_ip = current_master
                color = device_colors.get(master_ip, "orange")
                master_change_points.pop(0)
            else:
                # Use the color of the current master
                color = device_colors.get(current_master, "orange")

            ax1.plot([start_idx, end_idx], [sensor_data[start_idx], sensor_data[end_idx]], color=color)

        ax1.set_title("Photocell Data (Waveform)")
        ax1.set_xlabel("Time Index")
        ax1.set_ylabel("Sensor Value")

    else:
        ax1.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)

    # Plot Master Device Bar Chart
    if device_master_time:
        for ip, time_active in device_master_time.items():
            if ip not in device_colors:
                device_colors[ip] = next(color_cycle)
            ax2.bar(ip, time_active, color=device_colors[ip], label=f"{ip} ({time_active:.1f}s)")
        ax2.set_title("Master Device Duration")
        ax2.set_xlabel("Device IP")
        ax2.set_ylabel("Time as Master (s)")
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, "No master data available", ha="center", va="center", fontsize=12)
# Button Handler
def handle_button_press():
    global device_master_time, sensor_data, timestamps, master_change_points
    print("Button pressed! Resetting ESP8266 devices.")
    yellow_led.on()
    time.sleep(3)
    yellow_led.off()

    # Save current log file
    log_filename = f"master_logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(log_filename, "w") as log_file:
        log_file.write(f"Master History Log ({log_filename}):\n")
        for ip, time_active in device_master_time.items():
            log_file.write(f"Device {ip}: {time_active:.1f}s\n")
        log_file.write("\nRaw Sensor Data:\n")
        for timestamp, data in zip(timestamps, sensor_data):
            log_file.write(f"{timestamp} - {data}\n")
    print(f"Logs saved to {log_filename}")

    # Reset data for new log
    device_master_time.clear()
    sensor_data.clear()
    timestamps.clear()
    master_change_points.clear()

button.when_pressed = handle_button_press

# Start Socket Listener
thread = Thread(target=socket_listener, daemon=True)
thread.start()

# Create Graph
fig, (ax1, ax2) = plt.subplots(2, 1)
plt.subplots_adjust(hspace=0.5)

ani = FuncAnimation(fig, update_graph, interval=1000)

# Show Graph
try:
    plt.show()
except KeyboardInterrupt:
    print("Program interrupted.")
finally:
    sock.close()
