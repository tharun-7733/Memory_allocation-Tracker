import tracemalloc
import psutil
import time
import platform
import random
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

tracemalloc.start()

time_stamps = []
memory_used = []
memory_available = []
memory_cached = []
ram_usage = []
cpu_usage = []
swap_usage = []
disk_usage = []

fig, axes = plt.subplots(5, 1, figsize=(12, 12), facecolor="black")
plt.subplots_adjust(hspace=1)

fig_text = plt.figure(figsize=(10, 3), facecolor="black")
memory_text = fig_text.text(0.1, 0.80, "", fontsize=12, color="white", fontweight="bold", bbox=dict(facecolor="black", edgecolor="white"))
disk_text = fig_text.text(0.1, 0.70, "", fontsize=12, color="white", fontweight="bold", bbox=dict(facecolor="black", edgecolor="white"))
cpu_text = fig_text.text(0.1, 0.40, "", fontsize=12, color="white", fontweight="bold", bbox=dict(facecolor="black", edgecolor="white"))
swap_text = fig_text.text(0.1, 0.20, "", fontsize=12, color="white", fontweight="bold", bbox=dict(facecolor="black", edgecolor="white"))
paging_text = fig_text.text(0.1, 0.9, "", fontsize=12, color="white", fontweight="bold", bbox=dict(facecolor="black", edgecolor="white"))
segmentation_text = fig_text.text(0.1, 0.60, "", fontsize=12, color="white", fontweight="bold", bbox=dict(facecolor="black", edgecolor="white"))



# Cache Memory
def get_cached_memory():
    vm = psutil.virtual_memory()
    if platform.system() == "Darwin":
        return getattr(vm, 'inactive', 0) / (1024**3)
    return getattr(vm, 'cached', 0) / (1024**3)


# Paging
def get_paging():
    total_virtual_memory = 4 * 1024
    page_size = 4
    num_pages = total_virtual_memory // page_size
    page_table = {}
    for i in range(num_pages):
        page_table[i] = random.randint(0, num_pages - 1)
    return page_table


# Segmentation
def get_segmentation(memory_used):
    total_memory = psutil.virtual_memory().total / (1024**3)
    code_size = total_memory * 0.15
    data_size = total_memory * 0.25
    heap_size = total_memory * 0.30
    stack_size = total_memory * 0.10
    unused_size = total_memory - (code_size + data_size + heap_size + stack_size)
    segment_table = {
        "Code": {"Base": 0, "Limit": code_size},
        "Data": {"Base": code_size, "Limit": code_size + data_size},
        "Heap": {"Base": code_size + data_size, "Limit": code_size + data_size + heap_size},
        "Stack": {"Base": code_size + data_size + heap_size, "Limit": code_size + data_size + heap_size + stack_size},
        "Unused": {"Base": code_size + data_size + heap_size + stack_size, "Limit": total_memory}
    }
    return segment_table


# Update frames after every 10 seconds
def update(frame):
    total_memory = psutil.virtual_memory().total / (1024**3)
    used_memory = psutil.virtual_memory().used / (1024**3)
    available_memory = psutil.virtual_memory().available / (1024**3)
    cached_memory = get_cached_memory()
    ram = psutil.virtual_memory().percent
    total_disk = psutil.disk_usage('/').total / (1024**3)
    used_disk = psutil.disk_usage('/').used / (1024**3)
    available_disk = psutil.disk_usage('/').free / (1024**3)
    cpu = psutil.cpu_percent()
    swap = psutil.swap_memory().percent
    disk = psutil.disk_usage('/').percent

    time_stamps.append(time.strftime('%H:%M:%S'))
    memory_used.append(used_memory)
    memory_available.append(available_memory)
    memory_cached.append(cached_memory)
    ram_usage.append(ram)
    cpu_usage.append(cpu)
    swap_usage.append(swap)
    disk_usage.append(disk)

    if len(time_stamps) > 10:
        time_stamps.pop(0)
        memory_used.pop(0)
        memory_available.pop(0)
        memory_cached.pop(0)
        ram_usage.pop(0)
        cpu_usage.pop(0)
        swap_usage.pop(0)
        disk_usage.pop(0)


# Plot the axes on graph
    for ax in axes:
        ax.clear()

    # Cpu Usage
    axes[0].plot(time_stamps, cpu_usage, color='red', marker='o', label="CPU (%)")
    axes[0].set_ylabel("Usage (%)", color="white")
    axes[0].set_title("CPU Usage", color="white", fontsize=14)
    # Disk Usage
    axes[1].plot(time_stamps, disk_usage, color='magenta', linestyle='dashed', marker='x', label="Disk (%)")
    axes[1].set_ylabel("Usage (%)", color="white")
    axes[1].set_title("Disk Usage", color="white", fontsize=14)
    # Cache Usage
    axes[2].plot(time_stamps, memory_cached, color='cyan', linestyle='solid', marker='s', label="Cached Memory (GB)")
    axes[2].set_xlabel("Time", color="white")
    axes[2].set_ylabel("Memory (GB)", color="white")
    axes[2].set_title("Cached Memory", color="white", fontsize=14)
    # Ram Usage
    axes[3].plot(time_stamps, ram_usage, color='lime', linestyle='solid', marker='^', label="RAM (%)")
    axes[3].set_xlabel("Time", color="white")
    axes[3].set_ylabel("Usage (%)", color="white")
    axes[3].set_title("RAM Usage", color="white", fontsize=14)
    # Swap Usage
    axes[4].plot(time_stamps, swap_usage, color='yellow', linestyle='dashdot', marker='d', label="Swap (%)")
    axes[4].set_xlabel("Time", color="white")
    axes[4].set_ylabel("Usage (%)", color="white")
    axes[4].set_title("Swap Usage", color="white", fontsize=14)


    for ax in axes:
        ax.set_facecolor("black")
        ax.grid(True, linestyle="--", alpha=0.5, color="gray")
        ax.tick_params(axis='x', colors='white', rotation=45)
        ax.tick_params(axis='y', colors='white')
        ax.legend(facecolor="black", edgecolor="white", fontsize=8)
        for text in ax.legend().get_texts():
            text.set_color("white")

    memory_text.set_text(f"Total Memory: {total_memory:.2f} GB | Used: {used_memory:.2f} GB | Available: {available_memory:.2f} GB | Cached: {cached_memory:.2f} GB")
    disk_text.set_text(f"Disk Memory: {total_disk:.2f} GB | Used: {used_disk:.2f} GB | Available: {available_disk:.2f} GB")
    paging_text.set_text(f"Paging: {len(get_paging())} Pages")
    segmentation_text.set_text(f"Segmentation: Code: {get_segmentation(used_memory)['Code']['Limit']:.2f} GB")
    fig.canvas.draw()

ani = FuncAnimation(fig, update, interval=2000)
plt.show()
