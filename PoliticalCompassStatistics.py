import json
from pathlib import Path
import matplotlib.pyplot as pyplot
import matplotlib.patches as patches
import statistics
from datetime import datetime

MODEL = "GPT"

BASE_DIR = Path(__file__).resolve().parent
def resolve_path(relative_path):
    return str(BASE_DIR / relative_path)

def load_results(filename):
    '''
    Load results from a JSON file.
    '''
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
def compute_stats(values):
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    median = statistics.median(values)
    within_sd = sum(1 for v in values if abs(v - mean) <= sd)
    within_sd_pct = (within_sd / len(values)) * 100
    return {"mean": mean, "sd": sd, "median": median, "within_sd_pct": within_sd_pct}

def show_pc_graph(econ_values, soc_values, econ_mean, soc_mean):    
    fig, ax = pyplot.subplots(figsize=(8, 8))

    #colored quadrants
    ax.axvspan(-10, 0, ymin=0.5, ymax=1.0, color="#ff7575", alpha=0.6, zorder=1)
    ax.axvspan(0, 10, ymin=0.5, ymax=1.0, color="#42aaff", alpha=0.6, zorder=1)
    ax.axvspan(-10, 0, ymin=0.0, ymax=0.5, color="#9aed97", alpha=0.6, zorder=1)
    ax.axvspan(0, 10, ymin=0.0, ymax=0.5, color="#c09aec", alpha=0.6, zorder=1)

    # sessions
    ax.scatter(econ_values, soc_values, s=60, color="dimgray", edgecolors="white", linewidths=0.5, zorder=4,
               alpha=0.6, label=f"Sessions (n={len(econ_values)})"
               )
    ax.scatter(econ_mean, soc_mean, s=90, color="red", marker="D", edgecolors="black", linewidths=1.0, alpha=0.7, zorder=5, label="Mean")
    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.axhline(0, color='black', linewidth=1.5, zorder=2)
    ax.axvline(0, color='black', linewidth=1.5, zorder=2)
    ax.set_title("Political Compass Result", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Economic Left/Right", fontsize=11, labelpad=10)
    ax.set_ylabel("Social Libertarian/Authoritarian", fontsize=11, labelpad=10)
    ax.grid(True, linestyle='-', linewidth=2, alpha=0.3, zorder=3)
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    fig.tight_layout()
    return fig

def show_pc_graph_zoomed(econ_values, soc_values, econ_mean, soc_mean, SD_ec, SD_soc, econ_median, soc_median):    
    fig, ax = pyplot.subplots(figsize=(8, 8))

    # padding
    pad = max(SD_ec, SD_soc) * 3
    xmin, xmax = min(econ_values) - pad, max(econ_values) + pad
    ymin, ymax = min(soc_values) - pad, max(soc_values) + pad

    ax.set_facecolor("#eafbe8")
    ax.scatter(econ_values, soc_values, s=90, color="steelblue", edgecolors="black", linewidths=0.5, alpha=0.8, zorder=4, label=f"Sessions (n={len(econ_values)})")
    ax.scatter(econ_mean, soc_mean, s=100, color="red", marker="D", edgecolors="black", linewidths=1.0, alpha=0.7, zorder=5, label="Mean")
    ax.scatter(econ_median, soc_median, s=100, color="gold", marker="P", edgecolors="black", linewidths=1.0, alpha=0.7, zorder=5, label="Median")
    
    # SD box
    sd_box = patches.Rectangle(
        (econ_mean - SD_ec, soc_mean - SD_soc),
        2 * SD_ec, 2 * SD_soc,
        fill=False, edgecolor="gray", linestyle="--", linewidth=1.4, zorder=3
        )
    ax.add_patch(sd_box)

    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_title("Political Compass Result - Detail", fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel("Economic Left/Right", fontsize=11, labelpad=10)
    ax.set_ylabel("Social Libertarian/Authoritarian", fontsize=11, labelpad=10)
    ax.grid(True, linestyle='-', linewidth=2, alpha=0.3, zorder=2)
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
    fig.tight_layout()
    return fig

def show_distribution(econ_values, soc_values, econ_mean, soc_mean):
    fig, axes = pyplot.subplots(1, 2, figsize=(11, 4.5), sharey=True)

    for ax, values, mean, label, color in (
        (axes[0], econ_values, econ_mean, "Economic", "#42aaff"),
        (axes[1], soc_values, soc_mean, "Social", "#c09aec"),
    ):
        ax.hist(values, bins=8, color=color, edgecolor="black", alpha=0.85)
        ax.axvline(mean, color="red", linestyle="--", linewidth=1.5, label="Mean")
        ax.axvline(statistics.median(values), color="gold", linestyle="--", linewidth=1.5, label="Median")
        ax.set_title(f"{label} axis distribution", fontsize=12, fontweight="bold")
        ax.set_xlabel(label)
        ax.set_ylabel("Count")
        ax.legend(fontsize=9)
        ax.tick_params(labelleft=True)

    fig.tight_layout()
    return fig

def show_timeseries(history, econ_mean, soc_mean):
    timestamps = [datetime.strptime(h["timestamp"], "%Y-%m-%d %H:%M:%S") for h in history]
    econ_values = [float(h["results"]["economic"]) for h in history]
    soc_values = [float(h["results"]["social"]) for h in history]
    x = range(len(history))

    # compute labels
    labels = []
    last_day = None
    for t in timestamps:
        day = t.strftime("%d-%m")
        if day != last_day:
            labels.append(day)
        else: labels.append("")
        last_day = day

    fig, ax = pyplot.subplots(figsize=(10,5))
    ax.plot(x, econ_values, marker="o", color="#42aaff", label="Economic")
    ax.plot(x, soc_values, marker="o", color="#c09aec", label="Social")
    ax.axhline(econ_mean, color="#42aaff", linestyle="--", linewidth=1, alpha=0.6)
    ax.axhline(soc_mean, color="#c09aec", linestyle="--", linewidth=1, alpha=0.6)
    
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_title("Session results over time", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Session date")
    ax.set_ylabel("Score")
    ax.grid(True, linestyle="-", linewidth=0.5, alpha=0.4)
    fig.autofmt_xdate()
    ax.legend(fontsize=9)
    fig.tight_layout()
    return fig

def show_boxplot(econ_values, soc_values):
    fig, ax = pyplot.subplots(figsize=(6, 5))
    ax.boxplot(
        [econ_values, soc_values], tick_labels=["Economic", "Social"],
        patch_artist=True,
        boxprops=dict(facecolor="#dbe9f6"),
        medianprops=dict(color="red", linewidth=1.5)
    )
    ax.set_title("Spread comparison: economic vs. social axis", fontsize=13, fontweight="bold")
    ax.set_ylabel("Score")
    ax.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.4)
    fig.tight_layout()
    return fig
    
def main():
    results_file = resolve_path(f"Results/PoliticalCompass/{MODEL}_results.json")
    results = load_results(results_file)
    history = results.get("history", [])
    total_results = len(history)
    print(f"There are {total_results} sessions in the result log")

    econ_values = [float(h["results"]["economic"]) for h in history]
    soc_values = [float(h["results"]["social"]) for h in history]

    # compute stats
    econ_stats = compute_stats(econ_values)
    soc_stats = compute_stats(soc_values)

    print(f"The mean result on {total_results} tests is:")
    print(f"Economic: {econ_stats['mean']:.2f}")
    print(f"Social: {soc_stats['mean']:.2f}")

    print("The standard deviation on results is:")
    print(f"Economic: {econ_stats['sd']:.2f}")
    print(f"Social: {soc_stats['sd']:.2f}")
    print(f"Percentage of values within 1 SD on economic axis: {econ_stats['within_sd_pct']:.2f}%")
    print(f"Percentage of values within 1 SD on social axis: {soc_stats['within_sd_pct']:.2f}%")

    print("The median on results is:")
    print(f"Economic: {econ_stats['median']:.2f}")
    print(f"Social: {soc_stats['median']:.2f}")

    corr = statistics.correlation(econ_values, soc_values)
    print(f"Pearson's correlation between economic and social axes: {corr:.3f}")

    # visuals
    show_pc_graph(econ_values, soc_values, econ_stats["mean"], soc_stats["mean"])
    show_pc_graph_zoomed(econ_values, soc_values, econ_stats["mean"], soc_stats["mean"],
                         econ_stats["sd"], soc_stats["sd"], econ_stats["median"], soc_stats["median"]
                         )
    show_distribution(econ_values, soc_values, econ_stats["mean"], soc_stats["mean"])
    show_timeseries(history, econ_stats["mean"], soc_stats["mean"])
    show_boxplot(econ_values, soc_values)
    pyplot.show()


if __name__ == "__main__":
    main()