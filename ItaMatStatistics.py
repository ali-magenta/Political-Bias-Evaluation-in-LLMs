import json
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as pyplot
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

MODEL = "GPT"

BASE_DIR = Path(__file__).resolve().parent
def resolve_path(relative_path):
    return str(BASE_DIR / relative_path)
 
def load_results(filename):
    """Load results from a JSON file."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def parse_answer(answer):
    stance, pct_str = answer.split(" - ")
    pct = float(pct_str.rstrip("%"))
    score = pct
    return stance, pct, score

def build_dataframes(history):
    """
    Build two sessions x questions Dataframes, one with raw Si/No stance, one with score
    """
    score_rows = []
    stance_rows = []
    timestamps = []
    for entry in history:
        timestamps.append(datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S"))
        score_row = {}
        stance_row = {}
        for question, answer in entry["results"].items():
            stance, pct, score = parse_answer(answer)
            score_row[question] = score
            stance_row[question] = stance
        score_rows.append(score_row)
        stance_rows.append(stance_row)

    score_df = pd.DataFrame(score_rows, index=timestamps)
    stance_df = pd.DataFrame(stance_rows, index=timestamps)
    return score_df, stance_df

def compute_stats(score_df, stance_df):
    stats = pd.DataFrame({
        "mean_score": score_df.mean(),
        "median_score": score_df.median(),
        "sd_score": score_df.std(),
        "min_score": score_df.min(),
        "max_score": score_df.max(),
    })
    stats["range_score"] = stats["max_score"] - stats["min_score"]

    for question in score_df.columns:
        counts = stance_df[question].value_counts()
        stats.loc[question, "times_si_deciso"] = counts.get("Sì deciso", 0)
        stats.loc[question, "times_si"] = counts.get("Più per il Sì", 0)
        stats.loc[question, "times_neutrale"] = counts.get("Neutrale", 0)
        stats.loc[question, "times_no"] = counts.get("Più per il No", 0)
        stats.loc[question, "times_no_deciso"] = counts.get("No deciso", 0)

    return stats

def question_colors(questions):
    cmap = pyplot.colormaps.get_cmap("tab10")
    return {q: cmap(i / max(len(questions) - 1, 1)) for i, q in enumerate(questions)}

def short_labels(questions, max_len=28):
    out = []
    for q in questions:
        out.append(q if len(q) <= max_len else q[:max_len - 1] + "...")
    return out

def show_boxplot(score_df, colors):
    fig, ax = pyplot.subplots(figsize=(10,6))
    box = ax.boxplot([score_df[q] for q in score_df], tick_labels=short_labels(score_df),
                     patch_artist=True, medianprops=dict(color="black", linewidth=1.5))
    for patch, q in zip(box["boxes"], score_df.columns):
        patch.set_facecolor(colors[q])
        patch.set_alpha(0.75)

    all_scores = score_df.to_numpy().ravel()
    if all_scores.size:
        y_min = max(0, np.floor(all_scores.min()))
        y_max = min(100, np.ceil(all_scores.max()))
        span = y_max - y_min
        padding = max(5, span * 0.1)
        y_min = max(0, np.floor(y_min - padding))
        y_max = min(100, np.ceil(y_max + padding))

        if y_max - y_min < 20:
            y_min = max(0, y_min - 5)
            y_max = min(100, y_max + 5)
    else:
        y_min, y_max = 0, 100

    tick_step = 10 if (y_max - y_min) >= 20 else 5
    y_ticks = np.arange(np.ceil(y_min / tick_step) * tick_step, y_max + tick_step, tick_step)

    ax.set_ylim(y_min, y_max)
    ax.set_yticks(y_ticks)
    ax.axhline(0, color="gray", linewidth=1, linestyle="-", alpha=0.6)
    ax.set_title("Sì/No score distribution per question",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_ylabel("Score (0% totally No, 50% neutral, 100% totally Sì)")
    ax.set_xticklabels(short_labels(score_df), rotation=30, ha="right", fontsize=9)
    ax.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.4)
    fig.tight_layout()
    return fig

def show_mean_bar(stats, colors):
    fig, ax = pyplot.subplots(figsize=(10, 6))
    questions = stats.index
    ax.bar(short_labels(questions), stats["mean_score"], yerr=stats["sd_score"], capsize=4,
           color=[colors[q] for q in questions], edgecolor="black", alpha=0.9)
    ax.axhline(0, color="gray", linewidth=1, linestyle="-", alpha=0.6)
    ax.set_title("Mean Sì/No score per question (error bars = +-1 SD)",
                 fontsize=13, fontweight="bold", pad=15)
    ax.set_ylabel("Score (0% totally No, 50% neutral, 100% totally Sì)")
    ax.set_xticklabels(short_labels(questions), rotation=30, ha="right", fontsize=9)
    ax.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.4)
    fig.tight_layout()
    return fig

def day_change_labels(timestamps):
    labels = []
    last_day = None
    for t in timestamps:
        day = t.strftime("%d-%m")
        labels.append(day if day != last_day else "")
        last_day = day
    return labels
        

def show_heatmap(score_df):
    order = score_df.mean().sort_values(ascending=False).index
    data = score_df[order].to_numpy()

    fig, ax = pyplot.subplots(figsize=(9,8))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=100)

    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(short_labels(order), rotation=30, ha="right", fontsize=9)
    ax.set_yticklabels(range(len(score_df)))
    ax.set_yticklabels(day_change_labels(score_df.index), fontsize=8)
    ax.set_title("Sì/No score heatmap: session x question", fontsize=13, fontweight="bold", pad=15)
    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Score (0 No .. 50 neutral .. 100 Sì)")
    fig.tight_layout()
    return fig 

def show_small_multiples(score_df, colors):
    n = len(score_df.columns)
    n_cols = 2
    n_rows = -(-n // n_cols)
    fig, axes = pyplot.subplots(n_rows, n_cols, figsize=(11, 3 * n_rows), sharex=True, sharey=True)
    axes = axes.flatten()

    x = range(len(score_df))

    all_scores = score_df.to_numpy().ravel()
    if all_scores.size:
        y_min = max(0, np.floor(all_scores.min()))
        y_max = min(100, np.ceil(all_scores.max()))
        span = y_max - y_min
        padding = max(5, span * 0.1)
        y_min = max(0, np.floor(y_min - padding))
        y_max = min(100, np.ceil(y_max + padding))

        if y_max - y_min < 20:
            y_min = max(0, y_min - 5)
            y_max = min(100, y_max + 5)
    else:
        y_min, y_max = 0, 100

    tick_step = 10 if (y_max - y_min) >= 20 else 5
    y_ticks = np.arange(np.ceil(y_min / tick_step) * tick_step, y_max + tick_step, tick_step)

    for ax, q in zip(axes, score_df.columns):
        ax.plot(x, score_df[q], marker="o", markersize=3, linewidth=1.4, color=colors[q])
        ax.axhline(score_df[q].mean(), color="gray", linestyle="--", linewidth=1, alpha=0.6)
        ax.axhline(0, color="black", linestyle="-", linewidth=0.6, alpha=0.4)
        ax.set_title(short_labels([q])[0], fontsize=9, fontweight="bold")
        ax.set_ylim(y_min, y_max)
        ax.set_yticks(y_ticks)
        ax.tick_params(labelsize=7)
        ax.grid(True, linestyle="-", linewidth=0.4, alpha=0.3)

    for ax in axes[n:]:
        ax.axis("off")

    fig.suptitle("Sì/No score trend per question over sessions", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def show_stance_distribution(stats):
    questions = stats.index
    fig, ax = pyplot.subplots(figsize=(10, 6))

    ax.bar(short_labels(questions), stats["times_si_deciso"], color="#306f32", edgecolor="black", label="Sì deciso")
    ax.bar(short_labels(questions), stats["times_si"], bottom=stats["times_si_deciso"], color="#4caf50", edgecolor="black", label="Più per il Sì")
    ax.bar(short_labels(questions), stats["times_neutrale"], bottom=stats["times_si_deciso"]+stats["times_si"], color="#bdbdbd", edgecolor="black", label="Neutrale")
    ax.bar(short_labels(questions), stats["times_no"], bottom=stats["times_si_deciso"]+stats["times_si"]+stats["times_neutrale"], color="#e57373",
        edgecolor="black", label="Più per il No")
    ax.bar(short_labels(questions), stats["times_no_deciso"], bottom=stats["times_si_deciso"]+stats["times_si"]+stats["times_neutrale"]+stats["times_no"],
           color="#aa2020", edgecolor="black", label="No deciso")
    ax.set_title("Stance distribution per question (session count)", fontsize=13, fontweight="bold", pad=15)
    ax.set_ylabel("Number of sessions")
    ax.set_xticklabels(short_labels(questions), rotation=30, ha="right", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.4)
    fig.tight_layout()
    return fig    

def compute_correlation_and_pvalues(score_df):
    questions = score_df.columns
    corr = score_df.corr()
    pvalues = pd.DataFrame(index=questions, columns=questions, dtype=float)
    for qi in questions:
        for qj in questions:
            if qi == qj:
                pvalues.loc[qi, qj] = 0.0
            else:
                _, p = pearsonr(score_df[qi], score_df[qj])
                pvalues.loc[qi, qj] = p
    return corr, pvalues

def show_correlation_heatmap(score_df, alpha=0.05):
    corr, pvalues = compute_correlation_and_pvalues(score_df)

    fig, ax = pyplot.subplots(figsize=(8, 7))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="coolwarm")

    ax.set_xticks(range(len(corr.columns)))
    ax.set_xticklabels(short_labels(corr.columns), rotation=30, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr.columns)))
    ax.set_yticklabels(short_labels(corr.columns), fontsize=8)

    for i, qi in enumerate(corr.index):
        for j, qj in enumerate(corr.columns):
            r = corr.iloc[i, j]
            p = pvalues.loc[qi, qj]
            significant = (i != j) and (p < alpha)
            label = f"{r:.2f}{'*' if significant else ''}"
            ax.text(j, i, label, ha="center", va="center", fontsize=8,
                    color="black" if abs(r) < 0.6 else "white")
            if significant:
                ax.add_patch(pyplot.Rectangle((j-0.5, i-0.5), 1, 1, fill=False, edgecolor="black", linewidth=2))

    ax.set_title("Correlation between questions' Sì/No score across sessions\n"
                 f"(* statistically significant, p < {alpha})",
                 fontsize=12, fontweight="bold", pad=15)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson r")
    fig.tight_layout()
    return fig

def main():
    results_file = resolve_path(f"Results/ItaMat/{MODEL}_results_IM.json")
    results = load_results(results_file)
    history = results.get("history", [])

    score_df, stance_df = build_dataframes(history)
    stats = compute_stats(score_df, stance_df)

    print(f"There are {len(score_df)} sessions in the result log\n")
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda v: f"{v:.2f}")
    print(stats)

    colors = question_colors(score_df.columns)

    show_boxplot(score_df, colors)
    show_mean_bar(stats, colors)
    show_heatmap(score_df)
    show_small_multiples(score_df, colors)
    show_stance_distribution(stats)
    show_correlation_heatmap(score_df)
    pyplot.show()

if __name__ == "__main__":
    main()