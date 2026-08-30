import json
import math
import os
import pathlib
import subprocess
import webbrowser
from collections import defaultdict

MASTERED_INTERVAL = 14

# Raw cosines from this model sit in a narrow +0.58..+0.76 band: every pair of
# texts shares a large common component that swamps the real signal, so no
# absolute threshold separates related words from unrelated ones.
#
# Subtracting the mean vector removes that shared component and spreads the
# scores across roughly -0.24..+0.20, where a threshold becomes meaningful and
# genuinely unrelated words simply stay disconnected.
#
# A fixed cut-off drifts as the vocabulary grows: the pair count rises with the
# square of the words, so more of them clear any given value until the edges
# chain into a single blob. The cut-off therefore tracks a percentile of the
# scores, with a floor so an unrelated vocabulary stays unconnected rather than
# being forced to yield its top few percent.
SIMILARITY_FLOOR = 0.05
SIMILARITY_PERCENTILE = 0.94

# Of the eight hues in the data-viz reference palette, only two four-colour
# subsets clear the all-pairs colour-blindness and separation gates in both
# themes; five clear none. A network puts every cluster next to every other, so
# all-pairs is the applicable gate. The largest clusters take these hues and the
# rest stay neutral, rather than cycling into colours that cannot be told apart.
#
# Two results carry conditions: green/yellow lands in the CVD warn band on dark,
# and yellow/magenta fall below 3:1 on light. Both are permitted only alongside
# an encoding other than colour, which is why clusters are also laid out apart
# and labelled directly.
CLUSTER_PALETTE = {
    "light": ["#4a3aa7", "#e87ba4", "#008300", "#eda100"],
    "dark": ["#9085e9", "#d55181", "#008300", "#c98500"],
}

OUTPUT_FILE = "graph.html"

CDN = "https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.js"


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))

    return dot / norm if norm else 0.0


def centered(vectors):
    """Remove the component every embedding shares, which carries no meaning."""
    words = list(vectors)
    size = len(vectors[words[0]])
    mean = [sum(vectors[w][i] for w in words) / len(words) for i in range(size)]

    return {w: [value - mean[i] for i, value in enumerate(vectors[w])] for w in words}


def similarity_edges(words):
    vectors = {}
    for row in words:
        if row.get("embedding"):
            vectors[row["word"]] = json.loads(row["embedding"])

    # Centering needs a population to average over; below that, nothing to draw.
    if len(vectors) < 3:
        return []

    vectors = centered(vectors)

    names = list(vectors)
    scores = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            scores[(a, b)] = cosine(vectors[a], vectors[b])

    ranked = sorted(scores.values())
    cutoff = max(SIMILARITY_FLOOR, ranked[int(SIMILARITY_PERCENTILE * len(ranked))])

    edges = [
        {"from": a, "to": b, "value": score, "title": f"similarity {score:+.2f}"}
        for (a, b), score in scores.items()
        if score >= cutoff
    ]

    return sorted(edges, key=lambda e: e["value"], reverse=True)


def source_edges(words):
    by_source = defaultdict(list)
    for row in words:
        by_source[row["source"] or "unknown"].append(row)

    nodes = []
    edges = []
    for source, rows in by_source.items():
        hub = f"source::{source}"
        nodes.append({"id": hub, "label": source, "cluster": None})
        edges.extend({"from": hub, "to": row["word"]} for row in rows)

    return nodes, edges


def clusters(names, edges):
    """Connected components, largest first."""
    parent = {name: name for name in names}

    def root(name):
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    for edge in edges:
        if edge["from"] in parent and edge["to"] in parent:
            parent[root(edge["from"])] = root(edge["to"])

    grouped = defaultdict(list)
    for name in names:
        grouped[root(name)].append(name)

    return sorted(grouped.values(), key=lambda members: (-len(members), members[0]))


def central_word(members, edges):
    """The member carrying the most similarity weight names the cluster."""
    inside = set(members)
    weight = defaultdict(float)
    for edge in edges:
        if edge["from"] in inside and edge["to"] in inside:
            weight[edge["from"]] += edge.get("value", 0)
            weight[edge["to"]] += edge.get("value", 0)

    return max(members, key=lambda word: (weight[word], -len(word)))


def layout(groups):
    """Seed each cluster around its own centre.

    Physics alone starts from noise and drags overlapping clusters apart while
    the viewer watches; starting them apart converges quicker and calmer.
    """
    positions = {}
    spread = 320 + 90 * len(groups)

    for index, members in enumerate(groups):
        angle = 2 * math.pi * index / max(len(groups), 1)
        cx, cy = spread * math.cos(angle), spread * math.sin(angle)
        radius = 30 + 22 * len(members)

        for offset, word in enumerate(members):
            local = 2 * math.pi * offset / max(len(members), 1)
            positions[word] = (
                cx + radius * math.cos(local),
                cy + radius * math.sin(local),
            )

    return positions


def build_graph(words):
    edges = similarity_edges(words)
    hubs = []

    if not edges:
        # Nothing embedded yet: fall back to grouping by where words came from.
        hubs, edges = source_edges(words)

    names = [row["word"] for row in words]
    groups = clusters(names, edges)
    positions = layout(groups)

    degree = defaultdict(int)
    for edge in edges:
        degree[edge["from"]] += 1
        degree[edge["to"]] += 1

    colour_of = {}
    for index, members in enumerate(groups):
        for word in members:
            # Lone words get no hue: a colour would imply a grouping they lack.
            colour_of[word] = index if len(members) > 1 else None

    nodes = [
        {
            "id": row["word"],
            "label": row["word"],
            "cluster": colour_of.get(row["word"]),
            "mastered": (row["interval"] or 0) >= MASTERED_INTERVAL,
            "synonym": row["simple_synonym"],
            "definition": row["definition"],
            "context": row["context"],
            "source": row["source"],
            "url": row.get("article_url"),
            # Well-connected words read as anchors, lone ones stay quiet.
            "size": 9 + 3.2 * math.sqrt(degree[row["word"]]),
            "x": round(positions[row["word"]][0]),
            "y": round(positions[row["word"]][1]),
        }
        for row in words
    ]
    nodes.extend({**hub, "mastered": False} for hub in hubs)

    legend = [
        {
            "cluster": index,
            "name": central_word(members, edges),
            "size": len(members),
            "words": sorted(members),
        }
        for index, members in enumerate(groups)
        if len(members) > 1
    ]
    alone = sorted(m[0] for m in groups if len(m) == 1)

    return nodes, edges, {"clusters": legend, "alone": alone}


def render_html(nodes, edges, legend):
    payload = json.dumps(
        {
            "nodes": nodes,
            "edges": edges,
            "legend": legend,
            "palette": CLUSTER_PALETTE,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")  # a literal </script> would close the tag early

    return (
        TEMPLATE.replace("__CDN__", CDN)
        .replace("__WORDS__", str(len(nodes)))
        .replace("__LINKS__", str(len(edges)))
        .replace("__DATA__", payload)
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WordMiner graph</title>
<script src="__CDN__"></script>
<style>
  :root {
    color-scheme: light;
    --surface:   #fcfcfb;
    --panel:     #ffffff;
    --line:      #e3e2dd;
    --ink:       #0b0b0b;
    --ink-soft:  #52514e;
    --ink-faint: #86847d;
    --neutral:   #9b9a93;
    --edge:      #c9c8c1;
    --shadow:    0 6px 24px rgba(0,0,0,.10);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --surface:   #1a1a19;
      --panel:     #242422;
      --line:      #37372f;
      --ink:       #ffffff;
      --ink-soft:  #c3c2b7;
      --ink-faint: #8b8a80;
      --neutral:   #6f6e66;
      --edge:      #3d3d36;
      --shadow:    0 6px 24px rgba(0,0,0,.5);
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --surface:   #1a1a19;
    --panel:     #242422;
    --line:      #37372f;
    --ink:       #ffffff;
    --ink-soft:  #c3c2b7;
    --ink-faint: #8b8a80;
    --neutral:   #6f6e66;
    --edge:      #3d3d36;
    --shadow:    0 6px 24px rgba(0,0,0,.5);
  }

  * { box-sizing: border-box; }
  html, body { height: 100%; margin: 0; }
  body {
    background: var(--surface);
    color: var(--ink);
    font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
  }
  #graph { position: absolute; inset: 0; }

  .panel {
    position: absolute;
    top: 20px; left: 20px;
    width: 260px;
    max-height: calc(100% - 40px);
    display: flex; flex-direction: column;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 12px;
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .panel header { padding: 16px 18px 12px; border-bottom: 1px solid var(--line); }
  .panel h1 { margin: 0; font-size: 15px; font-weight: 600; letter-spacing: -0.01em; }
  .panel .meta { margin-top: 3px; color: var(--ink-faint); font-size: 12px; font-variant-numeric: tabular-nums; }
  .panel .body { padding: 8px 8px 12px; overflow-y: auto; }

  .group {
    width: 100%;
    display: flex; align-items: baseline; gap: 9px;
    padding: 7px 10px;
    border: 0; border-radius: 8px;
    background: none; color: inherit;
    font: inherit; text-align: left; cursor: pointer;
  }
  .group:hover { background: color-mix(in srgb, var(--ink) 6%, transparent); }
  .group[aria-pressed="true"] { background: color-mix(in srgb, var(--ink) 10%, transparent); }
  .swatch { width: 9px; height: 9px; border-radius: 50%; flex: 0 0 auto; transform: translateY(1px); }
  .group .name { flex: 1; font-weight: 500; }
  .group .count { color: var(--ink-faint); font-size: 12px; font-variant-numeric: tabular-nums; }
  .alone { padding: 10px 10px 2px; color: var(--ink-faint); font-size: 12px; line-height: 1.7; }
  .alone b { display: block; margin-bottom: 3px; font-weight: 500; color: var(--ink-soft); }

  .hint {
    position: absolute; bottom: 20px; left: 20px;
    color: var(--ink-faint); font-size: 12px;
  }

  div.vis-tooltip {
    position: absolute;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 10px;
    box-shadow: var(--shadow);
    color: var(--ink);
    padding: 11px 13px;
    max-width: 330px;
    white-space: normal;
    font: 13px/1.55 ui-sans-serif, system-ui, sans-serif;
  }
  .tip { display: grid; gap: 8px; }
  .tip .word { font-weight: 600; font-size: 14px; }
  .tip .syn { color: var(--ink-soft); }
  .tip .ctx { color: var(--ink-soft); font-style: italic; }
  .tip .src { color: var(--ink-faint); font-size: 12px; }

  @media (max-width: 620px) {
    .panel { position: static; width: auto; margin: 12px; max-height: 38%; }
    #graph { top: auto; height: 62%; bottom: 0; }
    .hint { display: none; }
  }
</style>
</head>
<body>
<div id="graph"></div>

<aside class="panel">
  <header>
    <h1>Vocabulary graph</h1>
    <div class="meta">__WORDS__ words · __LINKS__ links</div>
  </header>
  <div class="body">
    <div id="groups"></div>
    <div class="alone" id="alone" hidden></div>
  </div>
</aside>

<div class="hint">Click a word to open its article</div>

<script>
const data = __DATA__;

const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isDark = () =>
  document.documentElement.dataset.theme === "dark" ||
  (document.documentElement.dataset.theme !== "light" &&
   matchMedia("(prefers-color-scheme: dark)").matches);

const hueFor = node => {
  const palette = data.palette[isDark() ? "dark" : "light"];
  return node.cluster === null || node.cluster >= palette.length
    ? css("--neutral")
    : palette[node.cluster];
};

// A mastered word is drawn hollow. Colour already carries the cluster, so
// progress needs a channel of its own rather than a second set of hues.
const paint = node => {
  const hue = hueFor(node);
  return {
    color: {
      background: node.mastered ? css("--surface") : hue,
      border: hue,
      highlight: { background: hue, border: css("--ink") },
      hover: { background: hue, border: css("--ink") },
    },
    borderWidth: node.mastered ? 3 : 1.5,
  };
};

// vis-network 9 assigns a string title with textContent, so markup would be
// shown literally. An element is inserted as-is, and building it here keeps
// every value escaped by the DOM rather than by hand.
function tooltip(node) {
  const tip = document.createElement("div");
  tip.className = "tip";

  const line = (cls, text) => {
    if (!text) return;
    const el = document.createElement("div");
    el.className = cls;
    el.textContent = text;
    tip.appendChild(el);
  };

  line("word", node.label);
  if (node.synonym) line("syn", "\u2248 " + node.synonym);
  line("def", node.definition);
  line("ctx", node.context);
  line("src", node.source && node.source + (node.url ? " \u00b7 click to open the article" : ""));

  return tip;
}

const nodes = new vis.DataSet(
  data.nodes.map(n => ({ ...n, ...paint(n), title: tooltip(n) }))
);
const edges = new vis.DataSet(
  data.edges.map((e, i) => ({ id: "e" + i, ...e }))
);

const network = new vis.Network(
  document.getElementById("graph"),
  { nodes, edges },
  {
    nodes: {
      shape: "dot",
      size: 13,
      font: { size: 14, face: "ui-sans-serif, system-ui, sans-serif", vadjust: -2 },
      shadow: false,
    },
    edges: {
      width: 1,
      scaling: { min: 0.8, max: 4, label: false },
      smooth: { type: "continuous", roundness: 0.35 },
      selectionWidth: 2,
    },
    physics: {
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: -110,
        centralGravity: 0.006,
        springLength: 130,
        springConstant: 0.05,
        avoidOverlap: 0.35,
        damping: 0.35,
      },
      // Left running: dragging a word should pull its neighbours along and let
      // the rest settle back, rather than moving one frozen dot.
      stabilization: { iterations: 400, updateInterval: 40 },
      minVelocity: 0.4,
      timestep: 0.4,
    },
    interaction: {
      hover: true,
      tooltipDelay: 120,
      navigationButtons: false,
      dragNodes: true,
      hideEdgesOnDrag: false,
    },
  }
);

// --- focus ------------------------------------------------------------------
const fade = (hex, alpha) => {
  const v = parseInt(hex.replace("#", ""), 16);
  return `rgba(${(v >> 16) & 255}, ${(v >> 8) & 255}, ${v & 255}, ${alpha})`;
};

let focused = null;
let labelled = true;

// Hovering pushes everything but the word and its neighbours into the
// background, so a single thread can be followed through a dense patch.
function focus(id) {
  focused = id && nodes.get(id) ? id : null;
  const near = focused
    ? new Set([focused, ...network.getConnectedNodes(focused)])
    : null;

  nodes.update(data.nodes.map(node => {
    const lit = !near || near.has(node.id);
    const hue = hueFor(node);
    const ink = !labelled
      ? "rgba(0,0,0,0)"
      : lit ? css("--ink") : fade(css("--ink"), 0.22);

    if (lit) return { id: node.id, ...paint(node), font: { color: ink } };

    return {
      id: node.id,
      color: {
        background: node.mastered ? fade(css("--surface"), 0.35) : fade(hue, 0.16),
        border: fade(hue, 0.28),
      },
      borderWidth: node.mastered ? 3 : 1.5,
      font: { color: ink },
    };
  }));

  edges.update(data.edges.map((edge, i) => {
    const lit = !near || (near.has(edge.from) && near.has(edge.to));
    return {
      id: "e" + i,
      color: {
        color: lit ? css("--edge") : fade(css("--edge"), 0.3),
        highlight: css("--ink-soft"),
        hover: css("--ink-soft"),
      },
    };
  }));
}

network.on("hoverNode", params => focus(params.node));
network.on("blurNode", () => focus(null));

// Labels collapse into noise when zoomed out far enough that dots overlap.
network.on("zoom", ({ scale }) => {
  const show = scale > 0.5;
  if (show !== labelled) {
    labelled = show;
    focus(focused);
  }
});

// --- theme ------------------------------------------------------------------
function repaint() {
  focus(focused);
  document.querySelectorAll(".swatch").forEach(el => {
    el.style.background = hueFor({ cluster: Number(el.dataset.cluster) });
  });
}
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", repaint);

// --- legend -----------------------------------------------------------------
const groupsEl = document.getElementById("groups");
let active = null;

data.legend.clusters.forEach(group => {
  const button = document.createElement("button");
  button.className = "group";
  button.type = "button";
  button.setAttribute("aria-pressed", "false");
  button.innerHTML =
    `<span class="swatch" data-cluster="${group.cluster}"></span>` +
    `<span class="name"></span><span class="count">${group.size}</span>`;
  button.querySelector(".name").textContent = group.name;
  button.title = group.words.join(", ");
  button.onclick = () => {
    active = active === group.cluster ? null : group.cluster;
    document.querySelectorAll(".group").forEach((el, i) =>
      el.setAttribute("aria-pressed", String(data.legend.clusters[i].cluster === active))
    );
    if (active === null) {
      network.unselectAll();
      network.fit({ animation: { duration: 400 } });
    } else {
      network.selectNodes(group.words);
      network.fit({ nodes: group.words, animation: { duration: 400 } });
    }
  };
  groupsEl.appendChild(button);
});

if (data.legend.alone.length) {
  const el = document.getElementById("alone");
  el.hidden = false;
  el.innerHTML = "<b>On their own</b>";
  el.append(data.legend.alone.join(", "));
}

// --- open the article --------------------------------------------------------
const urls = Object.fromEntries(data.nodes.filter(n => n.url).map(n => [n.id, n.url]));

let dragging = false;
network.on("dragStart", () => { dragging = false; });
network.on("dragging", () => { dragging = true; });

network.on("click", params => {
  // Letting go after dragging a word must not count as opening it.
  if (dragging) { dragging = false; return; }
  const url = urls[params.nodes[0]];
  if (url) window.open(url, "_blank", "noopener");
});

network.once("stabilizationIterationsDone", () => {
  network.fit({ animation: { duration: 500 } });
});

repaint();
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

    nodes, edges, legend = build_graph(words)
    path = pathlib.Path(OUTPUT_FILE).resolve()
    path.write_text(render_html(nodes, edges, legend), encoding="utf-8")

    opened = open_in_browser(path) if open_browser else False

    return path, opened
