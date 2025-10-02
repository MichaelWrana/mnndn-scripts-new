import re
import networkx as nx
from collections import defaultdict

_WEIGHTS_LINE_RE = re.compile(r'^\s*([^\s]+)\s+([^\s]+)\s+([+-]?\d+(?:\.\d+)?)\s*$')
# Endpoint tokens look like "London,+UnitedKingdom209" → label="London,+UnitedKingdom", id="209"
_ENDPOINT_RE = re.compile(r'^(.*?)(\d+)$')

def _norm_loc_token(label: str):
    """
    "London,+UnitedKingdom"  -> ("london", "unitedkingdom")
    "New+York,+NY"           -> ("new york", "ny")
    If no comma is present, country becomes "".
    """
    s = label.replace('+', ' ')
    if ',' in s:
        city, country = s.split(',', 1)
        return city.strip().casefold(), country.strip().casefold()
    return s.strip().casefold(), ""

def _parse_endpoint_label(tok: str):
    """
    Extract just the location label (ignoring trailing digits).
      "London,+UnitedKingdom209" -> "London,+UnitedKingdom"
      "Paris,+France193"         -> "Paris,+France"
    If no trailing digits, use whole token as label.
    """
    m = _ENDPOINT_RE.match(tok)
    return (m.group(1) if m else tok)

def load_location_data_into_graph(
    G: nx.Graph,
    data_path: str,
    attr: str = "delay",
    also_set_weight: bool = True,
    include_external: bool = False,     # match edges touching nodes with data['external']==True ?
    aggregator: str = "min"             # 'min' | 'max' | 'mean' | 'first' | 'last'
):
    """
    Parse a RocketFuel-style weights file where endpoints are location+ID tokens
    (e.g., 'London,+UnitedKingdom209'). Ignore IDs; match by (city,country).

    For each line "LocA LocB value":
      - find node sets UA, UB in G with (city,country) == LocA/LocB
      - set edge[attr]=value (and 'weight' if also_set_weight) for all existing edges
        (u in UA, v in UB) (undirected). For same-loc pairs, apply to edges within UA.

    Returns a report dict.
    """
    if aggregator not in {"min", "max", "mean", "first", "last"}:
        raise ValueError("aggregator must be one of {'min','max','mean','first','last'}")

    # Build (city,country) -> set(node_ids) index from the graph
    loc_to_nodes = defaultdict(set)
    for nid, data in G.nodes(data=True):
        if (not include_external) and data.get("external"):
            continue
        city = (data.get("city") or "").strip()
        country = (data.get("country") or "").strip()
        key = (city.casefold(), country.casefold())
        if key != ("",""):
            loc_to_nodes[key].add(nid)

    # Accumulate values per (locA,locB) pair (order-insensitive)
    vals_by_pair = defaultdict(list)
    bad_lines = 0
    lines_total = 0
    with open(data_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            lines_total += 1
            m = _WEIGHTS_LINE_RE.match(s)
            if not m:
                bad_lines += 1
                continue
            a_tok, b_tok, val_s = m.groups()
            try:
                a_label = _parse_endpoint_label(a_tok)
                b_label = _parse_endpoint_label(b_tok)
                a_key = _norm_loc_token(a_label)
                b_key = _norm_loc_token(b_label)
                val = float(val_s)
            except Exception:
                bad_lines += 1
                continue
            pair = tuple(sorted((a_key, b_key)))
            vals_by_pair[pair].append(val)

    # Reduce duplicates per location-pair
    def _reduce(vals):
        if aggregator == "min":   return min(vals)
        if aggregator == "max":   return max(vals)
        if aggregator == "mean":  return sum(vals)/len(vals)
        if aggregator == "first": return vals[0]
        if aggregator == "last":  return vals[-1]

    pair_value = {pair: _reduce(vs) for pair, vs in vals_by_pair.items()}

    # Apply to edges
    edges_updated = 0
    pairs_applied = 0
    pairs_with_missing_location = []
    pairs_with_zero_edges = []

    for (locA, locB), val in pair_value.items():
        UA = loc_to_nodes.get(locA, set())
        UB = loc_to_nodes.get(locB, set())

        if not UA or not UB:
            pairs_with_missing_location.append({
                "locA": locA, "locB": locB, "sizeA": len(UA), "sizeB": len(UB)
            })
            continue

        updated_here = 0
        if locA == locB:
            # same-location: annotate edges within UA
            UAs = sorted(UA)
            Uset = set(UA)
            for u in UAs:
                for v in G[u]:
                    if v in Uset and v > u:  # avoid double-count
                        G[u][v][attr] = val
                        if also_set_weight:
                            G[u][v]["weight"] = val
                        updated_here += 1
        else:
            # cross-location: annotate edges between UA and UB
            UB_set = set(UB)
            for u in UA:
                for v in G[u]:
                    if v in UB_set:
                        a, b = (u, v) if u < v else (v, u)
                        # set once per edge
                        if attr not in G[a][b] or G[a][b][attr] != val:
                            G[a][b][attr] = val
                            if also_set_weight:
                                G[a][b]["weight"] = val
                            updated_here += 1

        if updated_here > 0:
            edges_updated += updated_here
            pairs_applied += 1
        else:
            pairs_with_zero_edges.append({
                "locA": locA, "locB": locB, "sizeA": len(UA), "sizeB": len(UB)
            })

    return {
        "lines_total": lines_total,
        "bad_lines": bad_lines,
        "unique_location_pairs": len(pair_value),
        "pairs_applied": pairs_applied,
        "edges_updated": edges_updated,
        "pairs_with_missing_location": pairs_with_missing_location[:10],  # sample
        "pairs_with_zero_edges": pairs_with_zero_edges[:10],              # sample
        "attr": attr,
        "aggregator": aggregator,
        "also_set_weight": also_set_weight,
        "include_external": include_external,
    }
