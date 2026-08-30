import html
import json
import math
import os
import pathlib
import subprocess
import webbrowser
from collections import defaultdict

MASTERED_INTERVAL = 14

# Cosine scores from this model sit in a narrow band (~0.55-0.75), so an absolute
# threshold is either empty or complete. Each word keeps its NEIGHBOURS closest
# peers instead, which adapts to whatever the spread happens to be.
NEIGHBOURS = 2

OUTPUT_FILE = "graph.html"

CDN = "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.js"


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))

    return dot / norm if norm else 0.0


def similarity_edges(words):
    vectors = {}
    for row in words:
        if row.get("embedding"):
            vectors[row["word"]] = json.loads(row["embedding"])

    scores = {}
    names = list(vectors)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            scores[(a, b)] = cosine(vectors[a], vectors[b])

    # Undirected: an edge survives if either endpoint ranks the other in its top k.
    kept = set()
    for word in names:
        ranked = sorted(
            (p for p in scores if word in p),
            key=lambda p: scores[p],
            reverse=True,
        )
        kept.update(ranked[:NEIGHBOURS])

    return [
        {
            "from": a,
            "to": b,
            "value": scores[(a, b)],
            "title": f"similarity {scores[(a, b)]:.2f}",
        }
        for a, b in sorted(kept, key=lambda p: scores[p], reverse=True)
    ]


def source_edges(words):
    by_source = defaultdict(list)
    for row in words:
        by_source[row["source_url"] or "unknown"].append(row)

    nodes = []
    edges = []
    for source, rows in by_source.items():
        hub = f"source::{source}"
        nodes.append({"id": hub, "label": source, "group": "source"})
        edges.extend({"from": hub, "to": row["word"]} for row in rows)

    return nodes, edges


def build_graph(words):
    nodes = [
        {
            "id": row["word"],
            "label": row["word"],
            "group": "mastered"
            if (row["interval"] or 0) >= MASTERED_INTERVAL
            else "learning",
            "title": tooltip(row),
        }
        for row in words
    ]

    edges = similarity_edges(words)
    if not edges:
        # Nothing embedded yet: fall back to grouping by where words came from.
        hubs, edges = source_edges(words)
        nodes.extend(hubs)

    return nodes, edges


def tooltip(row):
    parts = [f"<b>{html.escape(row['word'])}</b>"]

    if row["simple_synonym"]:
        parts.append(f"≈ {html.escape(row['simple_synonym'])}")
    if row["definition"]:
        parts.append(html.escape(row["definition"]))
    if row["context"]:
        parts.append(f"<i>{html.escape(row['context'])}</i>")

    return "<br><br>".join(parts)


def render_html(nodes, edges):
    # </script> inside the data would close the tag early.
    data = json.dumps({"nodes": nodes, "edges": edges}, ensure_ascii=False).replace(
        "</", "<\\/"
    )

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>WordMiner graph</title>
<script src="{CDN}"></script>
<style>
  html, body {{ margin: 0; height: 100%; background: #14161a; }}
  #graph {{ width: 100%; height: 100%; }}
  #hint {{
    position: fixed; top: 12px; left: 16px; z-index: 1;
    font: 13px system-ui, sans-serif; color: #8a929e;
  }}
  div.vis-tooltip {{
    background: #1e222a; border: 1px solid #333a45; border-radius: 6px;
    color: #dfe3e8; padding: 10px 12px; max-width: 340px;
    white-space: normal; font: 13px/1.5 system-ui, sans-serif;
    box-shadow: 0 6px 20px rgba(0,0,0,.45);
  }}
</style>
</head>
<body>
<div id="hint">{len(nodes)} nodes &middot; hover a word for its definition</div>
<div id="graph"></div>
<script>
const data = {data};

const groups = {{
  learning: {{ color: {{ background: "#3d6fd1", border: "#5b8ae8" }} }},
  mastered: {{ color: {{ background: "#2f8f5b", border: "#46b177" }} }},
  source: {{
    shape: "box",
    color: {{ background: "#2a2f38", border: "#454c58" }},
    font: {{ color: "#9aa3af", size: 13 }},
  }},
}};

new vis.Network(document.getElementById("graph"), data, {{
  groups: groups,
  nodes: {{
    shape: "dot",
    size: 16,
    font: {{ color: "#e6e9ed", size: 15, face: "system-ui" }},
    borderWidth: 2,
  }},
  edges: {{
    color: {{ color: "#39414d", highlight: "#6b7686" }},
    width: 1.5,
    scaling: {{ min: 1, max: 6, label: false }},
    smooth: {{ type: "continuous" }},
  }},
  physics: {{
    solver: "forceAtlas2Based",
    forceAtlas2Based: {{ gravitationalConstant: -60, springLength: 120 }},
    stabilization: {{ iterations: 300 }},
  }},
  interaction: {{ hover: true, tooltipDelay: 120 }},
}});
</script>
</body>
</html>
"""


def is_wsl():
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        return "microsoft" in pathlib.Path("/proc/version").read_text().lower()
    except OSError:
        return False


def open_in_browser(path):
    # WSL has no Linux browser installed, so hand the file to the Windows host.
    if is_wsl():
        try:
            windows_path = subprocess.run(
                ["wslpath", "-w", str(path)],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            # explorer.exe reports a non-zero exit code even when it succeeds.
            subprocess.run(["explorer.exe", windows_path], check=False)
            return True
        except (OSError, subprocess.SubprocessError):
            pass

    return webbrowser.open(path.as_uri())


def show_graph(words, open_browser=True):
    if not words:
        return None

    nodes, edges = build_graph(words)
    path = pathlib.Path(OUTPUT_FILE).resolve()
    path.write_text(render_html(nodes, edges), encoding="utf-8")

    opened = open_in_browser(path) if open_browser else False

    return path, opened
