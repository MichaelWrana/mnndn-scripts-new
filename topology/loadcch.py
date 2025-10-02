import re
import ipaddress
import networkx as nx
from collections import defaultdict

# ---------- permissive CCH line parser (as discussed) ----------

_NEIGH_RE   = re.compile(r'<\s*(-?\d+)\s*>')
_EXT_RE     = re.compile(r'\{\s*(-?\d+)\s*\}')
_RADIUS_RE  = re.compile(r'\br(\d+)\b')
_NAME_RE    = re.compile(r'=\s*([^\s]+)')

def _split_loc_token(loc_token: str):
    # '@Vienna,+Austria' → ('Vienna', 'Austria')
    loc = loc_token[1:].replace('+', ' ')
    if ',' in loc:
        city, country = loc.split(',', 1)
        return city.strip(), country.strip()
    return loc.strip(), None

def parse_cch_line(s: str):
    """
    Return a dict with fields or None if the line can't be parsed.
    Fields: rid, city, country, name, radius, external(bool), neighbors(list[int]), ext_refs(list[int])
    Handles both full router lines and stub lines like: '-1 =62.197.128.1 r1'
    """
    s = s.strip()
    if not s or s.startswith('#'):
        return None

    # ID
    parts = s.split()
    try:
        rid = int(parts[0])
    except Exception:
        return None

    # Stub-only line: "-1 =62.197.128.1 r1" (no neighbors)
    if s.startswith('-') and '<' not in s:
        m_name = _NAME_RE.search(s)
        m_rad  = _RADIUS_RE.search(s)
        if not (m_name and m_rad):
            return None
        return {
            'rid': rid,
            'city': None, 'country': None,
            'name': m_name.group(1),
            'radius': int(m_rad.group(1)),
            'external': True,
            'neighbors': [],
            'ext_refs': []
        }

    # Full router line
    m_loc = re.search(r'@([^\s]+)', s)
    m_name = _NAME_RE.search(s)
    m_rad  = _RADIUS_RE.search(s)
    if not (m_loc and m_name and m_rad):
        return None

    loc_token = '@' + m_loc.group(1)
    city, country = _split_loc_token(loc_token)
    neighbors = [int(x) for x in _NEIGH_RE.findall(s)]
    ext_refs  = [int(x) for x in _EXT_RE.findall(s)]

    return {
        'rid': rid,
        'city': city, 'country': country,
        'name': m_name.group(1),
        'radius': int(m_rad.group(1)),
        'external': rid < 0,
        'neighbors': neighbors,
        'ext_refs': ext_refs
    }

# ---------- file-level wrappers ----------

def parse_cch_file(cch_path: str):
    """
    Parse entire .cch. Returns (records, bad_lines)
    - records: list of dicts returned by parse_cch_line (non-None)
    - bad_lines: list of (lineno, text) that failed to parse
    """
    records, bad = [], []
    with open(cch_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            rec = parse_cch_line(line)
            if rec is None:
                # ignore empty/comment lines; keep the rest for debugging
                s = line.strip()
                if s and not s.startswith('#'):
                    bad.append((i, line.rstrip('\n')))
                continue
            records.append(rec)
    return records, bad

def parse_al_file(al_path: str):
    """
    Parse .al. Returns (ips_by_rid, host_by_rid).
    - ips_by_rid[rid] = set of interface IPs
    - host_by_rid[rid] = set of interface hostnames (col 3 when not an IP)
    """
    ips_by_rid = defaultdict(set)
    host_by_rid = defaultdict(set)
    with open(al_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('#'):
                continue
            parts = s.split()
            if len(parts) < 3:
                continue
            rid = int(parts[0])
            ip = parts[1]
            label = parts[2]
            ips_by_rid[rid].add(ip)
            # treat col3 as hostname if it's not a literal IP
            try:
                ipaddress.ip_address(label)
            except ValueError:
                host_by_rid[rid].add(label)
    return ips_by_rid, host_by_rid

def build_graph_from_cch_al(
    cch_path: str,
    al_path: str | None = None,
    keep_stubs: bool = False
):
    """
    Build a NetworkX Graph from .cch (+ optional .al).
    - No auto-creation of placeholder INTERNAL nodes.
    - If keep_stubs=True, add negative-ID external stub nodes and edges to them.
    Returns (G, report) where report is a dict with quick sanity stats.
    """
    records, bad = parse_cch_file(cch_path)

    # First pass: materialize nodes from parsed records only
    nodes = {}  # rid -> attr
    for r in records:
        rid = r['rid']
        # Store basic attrs
        attr = {
            'city': r['city'],
            'country': r['country'],
            'name': r['name'],
            'radius': r['radius'],
            'external': r['external'],
            'alias_ips': set(),
            'iface_hostnames': set(),
        }
        # promote 'name' to hostname/primary_ip for convenience
        try:
            ipaddress.ip_address(r['name'])
            attr['primary_ip'] = r['name']
        except ValueError:
            attr['hostname'] = r['name']
        nodes[rid] = attr

    # Optional alias enrichment from .al
    if al_path:
        ips_by_rid, host_by_rid = parse_al_file(al_path)
        for rid, attr in nodes.items():
            if rid in ips_by_rid:
                attr['alias_ips'].update(ips_by_rid[rid])
            if rid in host_by_rid:
                attr['iface_hostnames'].update(host_by_rid[rid])

    # Second pass: build edges, no placeholder internal nodes
    G = nx.Graph()
    for rid, attr in nodes.items():
        G.add_node(rid, **attr)

    seen = set()
    missing_internal = set()
    for r in records:
        u = r['rid']
        if u < 0:
            continue  # don't source edges from stub records
        for v in r['neighbors']:
            if v >= 0:
                if v in nodes:
                    e = (min(u, v), max(u, v))
                    if e not in seen:
                        G.add_edge(*e)
                        seen.add(e)
                else:
                    missing_internal.add(v)
            else:
                if keep_stubs:
                    # materialize stub if it's not already present
                    if v not in G:
                        G.add_node(v, external=True, city=None, country=None,
                                   name=str(v), radius=None,
                                   alias_ips=set(), iface_hostnames=set())
                    e = (min(u, v), max(u, v))
                    if e not in seen:
                        G.add_edge(*e)
                        seen.add(e)

        # Optionally hook up explicit { -id } ext_refs too
        if keep_stubs:
            for v in r['ext_refs']:
                if v not in G:
                    G.add_node(v, external=True, city=None, country=None,
                               name=str(v), radius=None,
                               alias_ips=set(), iface_hostnames=set())
                e = (min(u, v), max(u, v))
                if e not in seen:
                    G.add_edge(*e)
                    seen.add(e)

    report = {
        'num_nodes': G.number_of_nodes(),
        'num_edges': G.number_of_edges(),
        'bad_lines': len(bad),
        'bad_line_samples': bad[:5],
        'missing_internal_ids': sorted(list(missing_internal))[:50],
        'num_missing_internal': len(missing_internal),
        'kept_stubs': keep_stubs,
    }
    return G, report

