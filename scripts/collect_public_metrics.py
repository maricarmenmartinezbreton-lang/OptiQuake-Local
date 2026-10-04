import json
import os
import pathlib
import urllib.request
from datetime import datetime, timezone

REPO = "maricarmenmartinezbreton-lang/OptiQuake-Local"
ZENODO_RECORD = "23005112"
OUT = pathlib.Path("metrics/latest.json")
MD = pathlib.Path("METRICS.md")


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def gh(path=""):
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "optiquake-metrics",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{REPO}"
    if path:
        url += f"/{path}"
    return get_json(url, headers)

repo = gh()
releases = gh("releases")
try:
    views = gh("traffic/views")
    clones = gh("traffic/clones")
except Exception:
    views = {"count": None, "uniques": None}
    clones = {"count": None, "uniques": None}

release_downloads = sum(
    asset.get("download_count", 0)
    for release in releases
    for asset in release.get("assets", [])
)

zenodo = get_json(f"https://zenodo.org/api/records/{ZENODO_RECORD}")
pypi = get_json(
    "https://pypistats.org/api/packages/optiquake-local/recent"
).get("data", {})

snapshot = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "github": {
        "stars": repo.get("stargazers_count", 0),
        "forks": repo.get("forks_count", 0),
        "watchers": repo.get("subscribers_count", 0),
        "views_14d": views.get("count"),
        "unique_views_14d": views.get("uniques"),
        "clones_14d": clones.get("count"),
        "unique_cloners_14d": clones.get("uniques"),
        "release_asset_downloads": release_downloads,
    },
    "pypi": pypi,
    "zenodo": {
        "record": int(ZENODO_RECORD),
        "doi": zenodo.get("doi"),
        "version": zenodo.get("metadata", {}).get("version"),
        "views": zenodo.get("stats", {}).get("views"),
        "unique_views": zenodo.get("stats", {}).get("unique_views"),
        "downloads": zenodo.get("stats", {}).get("downloads"),
        "unique_downloads": zenodo.get("stats", {}).get("unique_downloads"),
    },
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

g = snapshot["github"]
z = snapshot["zenodo"]
lines = [
    "# Public reach metrics",
    "",
    f"Updated: **{snapshot['timestamp_utc']}**",
    "",
    (
        "These are public/platform-reported counters and may include "
        "automated traffic. They are not scientific validation metrics."
    ),
    "",
    "| Metric | Current |",
    "|---|---:|",
    f"| GitHub stars | {g['stars']} |",
    f"| GitHub forks | {g['forks']} |",
    f"| GitHub watchers | {g['watchers']} |",
    f"| GitHub views (14d) | {g['views_14d']} |",
    f"| GitHub unique viewers (14d) | {g['unique_views_14d']} |",
    f"| GitHub clones (14d) | {g['clones_14d']} |",
    f"| GitHub unique cloners (14d) | {g['unique_cloners_14d']} |",
    f"| GitHub release asset downloads | {g['release_asset_downloads']} |",
    f"| PyPI downloads (last day) | {pypi.get('last_day')} |",
    f"| PyPI downloads (last week) | {pypi.get('last_week')} |",
    f"| PyPI downloads (last month) | {pypi.get('last_month')} |",
    f"| Zenodo views | {z['views']} |",
    f"| Zenodo unique views | {z['unique_views']} |",
    f"| Zenodo downloads | {z['downloads']} |",
    f"| Zenodo unique downloads | {z['unique_downloads']} |",
    "",
    (
        f"Latest archived Zenodo version: **{z['version']}** — "
        f"DOI `{z['doi']}`."
    ),
]

MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps(snapshot, ensure_ascii=False))
