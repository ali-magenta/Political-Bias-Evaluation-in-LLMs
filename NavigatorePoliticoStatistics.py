import json
from pathlib import Path
import matplotlib.pyplot as pyplot
from datetime import datetime
import pandas as pd

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
    
def build_dataframe(history):
    """
    Build a session x parties DataFrame
    """
    rows = []
    timestamps = []
    for entry in history:
        results = entry["results"]
        # skip results with old format
        if set(results.keys()) == {"party", "percentage"}:
            continue
        timestamps.append(datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S"))
        rows.append({party: float(pct.rstrip("%")) for party, pct in results.items()})

    df = pd.DataFrame(rows, index=timestamps)
    df = df[df.mean().sort_values(ascending=False).index]
    return df
    
def compute_stats(df):
    rank_df = df.rank(axis=1, ascending=False, method="average")

    stats = pd.DataFrame({
        "mean": df.mean(),
        "median": df.median(),
        "sd": df.std(),
        "min": df.min(),
        "max": df.max()
    })
    stats["range"] = stats["max"] - stats["min"]
    stats["cv_pct"] = (stats["sd"] / stats["mean"]) * 100
    stats["mean_rank"] = rank_df.mean()
    stats["median_rank"] = rank_df.median()
    stats["times_first"] = (rank_df == 1).sum()
    stats["times_top3"] = (rank_df <= 3).sum()
    stats = stats.sort_values("mean", ascending=False)
    
    return stats, rank_df

def party_colors(parties):
    cmap = pyplot.colormaps.get_cmap("tab20")
    return {party: cmap(i / max(len(parties) - 1,1)) for i, party in enumerate(parties)}

def day_change_labels(timestamps):
    labels = []
    last_day = None
    for t in timestamps:
        day = t.strftime("%d-%m")
        labels.append(day if day != last_day else "")
        last_day = day
    return labels

def show_rank_chart(rank_df, colors):
    fig, ax = pyplot.subplots(figsize=(12, 7))
    x = range(len(rank_df))

    for party in rank_df.columns:
        ax.plot(x, rank_df[party], marker="o", markersize=4, linewidth=1.6, color=colors[party], label=party, alpha=0.9)

    ax.set_yticks(range(1, len(rank_df.columns) + 1))
    ax.invert_yaxis()
    ax.set_xticks(list(x))
    ax.set_xticklabels(day_change_labels(rank_df.index), fontsize=8)
    ax.set_title("Party ranking by session", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Session date")
    ax.set_ylabel("Rank (1 = highest affinity)")
    ax.grid(True, linestyle="-", linewidth=0.5, alpha=0.3)
    ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.01, 0.5))
    fig.tight_layout()
    return fig

def show_mean_bar(stats, colors):
    fig, ax = pyplot.subplots(figsize=(11,6))
    parties = stats.index
    ax.bar(parties, stats["mean"], yerr=stats["sd"], capsize=4,
            color=[colors[p] for p in parties], edgecolor="black", alpha=0.9
           )
    ax.set_title("Mean affinity per party (error bars = +-1 SD)", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Affinity %")
    ax.set_xticklabels(parties, rotation=40, ha="right", fontsize=9)
    ax.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.4)
    fig.tight_layout()
    return fig

def show_heatmap(df):
    order = df.mean().sort_values(ascending=False).index
    data = df[order].to_numpy()

    fig, ax = pyplot.subplots(figsize=(10, 8))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn")

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=40, ha="right", fontsize=9)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(day_change_labels(df.index), fontsize=8)
    ax.set_title("Affinity heatmap: session x party", fontsize=14, fontweight="bold", pad=15)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Affinity %")
    fig.tight_layout()
    return fig

def show_boxplot(df, colors):
    order = df.median().sort_values(ascending=False).index
    fig, ax = pyplot.subplots(figsize=(11, 6))
    box = ax.boxplot(
        [df[p] for p in order], tick_labels=order, patch_artist=True,
        medianprops=dict(color="black", linewidth=1.5)
    )
    for patch, party in zip(box["boxes"], order):
        patch.set_facecolor(colors[party])
        patch.set_alpha(0.65)
    ax.set_title("Affinity distribution per party (sorted by median)", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Affinity %")
    ax.set_xticklabels(order, rotation=40, ha="right", fontsize=9)
    ax.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.4)
    fig.tight_layout()
    return fig

def show_small_multiples(df, colors):
    n = len(df.columns)
    n_cols = 3
    n_rows = -(-n // n_cols)
    fig, axes = pyplot.subplots(n_rows, n_cols, figsize=(13, 3 * n_rows), sharex=True)
    axes = axes.flatten()

    x = range(len(df))
    for ax, party in zip(axes, df.columns):
        ax.plot(x, df[party], marker="o", markersize=3, linewidth=1.4, color=colors[party])
        ax.axhline(df[party].mean(), color="gray", linestyle="--", linewidth=1, alpha=0.6)
        ax.set_title(party, fontsize=9, fontweight="bold")
        ax.tick_params(labelsize=7)
        ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.3)

    for ax in axes[n:]:
        ax.axis("off")

    fig.suptitle("Affinity trend per party over sessions", fontsize=14, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    return fig

def show_correlation_heatmap(df):
    corr = df.corr()
    fig, ax = pyplot.subplots(figsize=(9, 8))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")

    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(corr.columns, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr.columns)))
    ax.set_yticklabels(corr.columns, fontsize=8)

    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}", ha="center", va="center", fontsize=6,
                    color="black" if abs(corr.iloc[i, j]) < 0.6 else "white")

    ax.set_title("Correlation between parties' affinity across sessions", fontsize=13, fontweight="bold", pad=15)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson r")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig
    
def main():
    results_file = resolve_path(f"Results/NavigatorePolitico/{MODEL}_results_NP.json")
    results = load_results(results_file)
    history = results.get("history", [])

    df = build_dataframe(history)
    stats, rank_df = compute_stats(df)

    # print stats
    print (f"There are {len(df)} sessions in the result log")
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda v: f"{v:.2f}")
    print(stats)

    colors = party_colors(df.columns)

    # visuals
    show_rank_chart(rank_df, colors)
    show_boxplot(df, colors)
    show_mean_bar(stats, colors)
    show_heatmap(df)
    show_small_multiples(df, colors)
    show_correlation_heatmap(df)
    pyplot.show()


if __name__ == "__main__":
    main()