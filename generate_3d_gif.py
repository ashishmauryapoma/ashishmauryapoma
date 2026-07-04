"""
Fetches a GitHub user's contribution calendar via the GraphQL API,
renders it as a 3D bar chart, and saves a rotating GIF.
Requires env vars: GITHUB_TOKEN, USERNAME
"""
import os
import requests
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from PIL import Image
import io

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ["USERNAME"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            weekday
          }
        }
      }
    }
  }
}
"""

def fetch_contributions():
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": USERNAME}},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

    num_weeks = len(weeks)
    grid = np.zeros((7, num_weeks))
    for w_idx, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[day["weekday"], w_idx] = day["contributionCount"]
    return grid

def build_gif(grid, out_path="profile-3d-contrib.gif"):
    rows, cols = grid.shape
    xpos, ypos = np.meshgrid(np.arange(cols), np.arange(rows))
    xpos = xpos.flatten()
    ypos = ypos.flatten()
    zpos = np.zeros_like(xpos)
    dz = grid.flatten()
    dx = dy = 0.8

    # Color scale based on contribution intensity (GitHub green shades)
    max_val = dz.max() if dz.max() > 0 else 1
    colors = plt.cm.Greens(0.25 + 0.65 * (dz / max_val))

    frames = []
    n_frames = 36  # 36 frames * 10 deg = full 360 spin
    for i in range(n_frames):
        fig = plt.figure(figsize=(8, 4.5), dpi=100)
        ax = fig.add_subplot(111, projection="3d")
        ax.bar3d(xpos, ypos, zpos, dx, dy, dz, color=colors, shade=True)
        ax.set_axis_off()
        ax.view_init(elev=25, azim=i * (360 / n_frames))
        ax.set_box_aspect([cols / 7, 1, 2])
        fig.patch.set_alpha(0.0)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", transparent=True, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        frames.append(Image.open(buf).convert("RGBA"))

    # Normalize frame sizes
    w = max(f.width for f in frames)
    h = max(f.height for f in frames)
    padded = []
    for f in frames:
        bg = Image.new("RGBA", (w, h), (13, 17, 23, 255))  # GitHub dark bg
        bg.paste(f, ((w - f.width) // 2, (h - f.height) // 2), f)
        padded.append(bg.convert("RGB"))

    padded[0].save(
        out_path,
        save_all=True,
        append_images=padded[1:],
        duration=80,
        loop=0,
    )
    print(f"Saved {out_path} with {len(padded)} frames")

if __name__ == "__main__":
    grid = fetch_contributions()
    build_gif(grid)
