"""Dibujo de la pista, mapas de calor y recorridos (PNG)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: funciona en servidores
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from scipy.ndimage import gaussian_filter

from .court import COURT_LENGTH, COURT_WIDTH, FAR_SERVICE_Y, NEAR_SERVICE_Y, NET_Y


def _draw_court(ax) -> None:
    ax.add_patch(Rectangle((0, 0), COURT_WIDTH, COURT_LENGTH, fill=False, lw=2, ec="white"))
    ax.plot([0, COURT_WIDTH], [NET_Y, NET_Y], color="white", lw=3)
    for y in (NEAR_SERVICE_Y, FAR_SERVICE_Y):
        ax.plot([0, COURT_WIDTH], [y, y], color="white", lw=1.5)
    ax.plot([COURT_WIDTH / 2] * 2, [NEAR_SERVICE_Y, FAR_SERVICE_Y], color="white", lw=1.5)
    ax.set_xlim(-0.5, COURT_WIDTH + 0.5)
    ax.set_ylim(-0.5, COURT_LENGTH + 0.5)
    ax.set_aspect("equal")
    ax.set_facecolor("#2f6db5")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.text(COURT_WIDTH / 2, -0.4, "cámara", ha="center", va="top", fontsize=8, color="#444")


def save_heatmap(grid: np.ndarray, out_png: str | Path, title: str) -> Path:
    fig, ax = plt.subplots(figsize=(3.6, 6.4), dpi=110)
    _draw_court(ax)
    if grid.max() > 0:
        # Suavizado (sigma = 0,5 m) y transparencia proporcional: las zonas sin presencia dejan ver la pista.
        g = gaussian_filter(grid, sigma=1.0)
        g = g / g.max()
        rgba = plt.get_cmap("inferno")(g)
        rgba[..., 3] = np.clip(g**0.6 * 1.1, 0, 0.9)
        ax.imshow(rgba, extent=(0, COURT_WIDTH, 0, COURT_LENGTH), origin="lower", interpolation="bilinear", zorder=1)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return Path(out_png)


def save_trajectories(trajectories: dict[str, np.ndarray], out_png: str | Path, title: str = "Recorridos") -> Path:
    fig, ax = plt.subplots(figsize=(3.6, 6.4), dpi=110)
    _draw_court(ax)
    colors = ["#ffcc00", "#ff4d4d", "#4dff88", "#d580ff", "#ffffff", "#00e5ff"]
    for i, (pid, xy) in enumerate(trajectories.items()):
        if len(xy):
            ax.plot(xy[:, 0], xy[:, 1], lw=0.8, alpha=0.8, color=colors[i % len(colors)], label=pid)
    ax.legend(loc="upper right", fontsize=7, framealpha=0.6)
    ax.set_title(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)
    return Path(out_png)
