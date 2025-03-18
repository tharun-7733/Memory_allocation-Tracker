# Memmory allocation tracker Script

## Overview

This Python script monitors and visualizes system resource usage, including CPU, RAM, disk, swap, and cached memory. It also simulates paging and segmentation concepts for educational purposes.

## Features

- Real-time monitoring of CPU, RAM, disk, swap, and cached memory usage
- Visualization of resource trends over time using Matplotlib
- Simulated paging system with random memory page mappings
- Segmentation-based memory representation with code, data, heap, and stack segments
- Text-based real-time updates on system resource usage

## Requirements

Ensure you have the following dependencies installed before running the script:

```bash
pip install psutil matplotlib
```

## How to Run

1. Save the script as `system_monitor.py`.
2. Open a terminal and navigate to the directory where the script is saved.
3. Run the script using:

```bash
python system_monitor.py
```

4. The script will start monitoring and displaying system resource usage with real-time graphs and text updates.

## Explanation of Functions

- `get_cached_memory()`: Fetches cached memory depending on the OS.
- `get_paging()`: Simulates a simple paging system.
- `get_segmentation(memory_used)`: Simulates memory segmentation.
- `update(frame)`: Collects system resource data, updates lists, and refreshes graphs.

## Graphs & Display

The script generates five subplots representing:

1. CPU Usage (%)
2. Disk Usage (%)
3. Cached Memory (GB)
4. RAM Usage (%)
5. Swap Usage (%)

Additionally, a separate figure provides text-based real-time updates on system statistics.

## Customization

- Modify the `interval` parameter in `FuncAnimation` to adjust update frequency.
- Change colors, labels, or styles in the `update()` function to personalize graphs.

## License

This script is open-source and free to use for educational,school projects and monitoring purposes.

