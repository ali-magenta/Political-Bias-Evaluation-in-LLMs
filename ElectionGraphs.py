from pathlib import Path
import json
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

MODEL = "Grok"

BASE_DIR = Path(__file__).resolve().parent

def resolve_path(relative_path):
    return str(BASE_DIR / relative_path)

def load_results(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def show_election_bar_chart(results, title):
    other = "Other parties"
    results = sorted(results, key=lambda r: (r.get("party") != other, (r.get("percentage") or 0),), reverse=True)
    

    parties = [result.get("party") for result in results]
    percentages = [result.get("percentage") for result in results]
    bar_colors = [result.get("color") for result in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(parties, percentages, color=bar_colors, edgecolor="black", linewidth=0.8, width=0.8)

    for bar, perc in zip(bars, percentages):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(percentages) * 0.015,
        f"{perc:.1f}%", ha="center", va="bottom", fontsize=11, fontweight="bold") 

    ax.set_title(f"2022 Electoral Results for {title}", fontsize=15, fontweight="bold", pad=20, loc="center")
    ax.set_ylim(0, max(percentages) * 1.15)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(True, axis="y", linestyle="-", linewidth=0.6, alpha=0.4, zorder=0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.set_xticklabels(parties, rotation=30, ha="right", fontsize=10)
    ax.tick_params(axis="y", labelsize=9)

    fig.tight_layout()
    return fig

def compute_model_election_differences(results):
    model_values = {result["party"]: result[f"{MODEL}_mean"] for result in results}
    total_affinity = sum(model_values.values())

    for result in model_values:
        model_values[result] = model_values[result] / total_affinity if total_affinity > 0 else 0
        model_values[result] = round(model_values[result] * 100, 2)

    differences = {}

    for result in results:
        party = result["party"]
        model_percentage = model_values.get(party)
        election_percentage = result.get("percentage")
        differences[party] = round(model_percentage - election_percentage, 2)

    return differences

def show_model_election_diff_chart(results, differences):
    results = sorted(results, key=lambda r: r.get("percentage") or 0, reverse=True)
    results = [r for r in results if r.get("party") != "Other parties" and r.get("percentage") >= 2.5]
    parties = [r["party"] for r in results]
    colors = [r.get("color") for r in results]
    diffs = [differences[p] for p in parties]

    parties = parties[::-1]
    colors = colors[::-1]
    diffs = diffs[::-1]

    y_pos = range(len(parties))

    fig, ax = plt.subplots(figsize=(6, 7))
    ax.barh(y_pos, diffs, color=colors, edgecolor="black", linewidth=0.8, height=0.5, zorder=3)

    for y, party, diff in zip(y_pos, parties, diffs):
        if diff >= 0:
            label_x, ha = -0.8, "right"
        else:
            label_x, ha = 0.8, "left"
        ax.text(label_x, y, party, ha=ha, va="center", fontsize=10, zorder=4, bbox=dict(facecolor="white", edgecolor="none"))

    ax.axvline(0, color="black", linewidth=1.2, zorder=2)
    ax.set_xlim(-20, 20)
    ax.set_yticks([])
    ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.grid(True, axis="x", linestyle="-", linewidth=0.6, alpha=0.5, zorder=0)
    ax.set_axisbelow(True)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.set_title("Model-Elections differences normalized", fontsize=14, fontweight="bold", pad=15)

    fig.tight_layout()
    return fig

def compute_ranks(results):
    other = "Other parties"
    results = sorted(results, key=lambda r: (r.get("party") != other, (r.get("percentage") or 0),), reverse=True)

    election_ranks = [result.get("party") for result in results]
    election_ranks.pop()

    results = sorted(results, key=lambda r: (r.get(f"{MODEL}_mean")), reverse=True)
    GPT_ranks = [result.get("party") for result in results]
    GPT_ranks.pop()
    
    spearman = spearmanr(election_ranks, GPT_ranks)
    return spearman


def main():
    results_file = resolve_path("Results/ElectoralResults/results2022_camera.json")
    results = load_results(results_file)
    results = results.get("results", {})

    show_election_bar_chart(results, title="Senato della Repubblica")
    differences = compute_model_election_differences(results)
    show_model_election_diff_chart(results, differences)
    print(differences)
    # spearman = compute_ranks(results)
    # print(f"Spearman correlation: {spearman.correlation:.4f}")
    # print(f"Spearman pvalue: {spearman.pvalue:.4f}")
    plt.show()

if __name__ == "__main__":
    main()