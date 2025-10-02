import re, ipaddress, networkx as nx
from collections import Counter

# ---------------- pattern sets (same as last pass, minus nudges) ----------------

# DNS (strict + "auth" as a hint)
DNS_PATTERNS_STRICT = [
    r'(^|[.\-])dns\d*([.\-]|$)',
    r'(^|[.\-])resolver([.\-]|$)',
    r'(^|[.\-])bind([.\-]|$)',
    r'(^|[.\-])recursor([.\-]|$)',
    r'(^|[.\-])ns\d{1,3}([.\-]|$)',
]
DNS_PATTERNS_HINTS = [
    r'(^|[.\-])auth\d*([.\-]|$)',  # requested: treat "auth" as DNS-ish hint
]

# SERVER: expanded (direct name matches only)
SERVER_PATTERNS = [
    r'(^|[.\-])host(\d+)?([.\-]|$)',      # *.host.ebone.net
    r'(^|[.\-])vip(\d+)?([.\-]|$)',       # vip.ebone.net
    r'(^|[.\-])www\d*([.\-]|$)', r'(^|[.\-])web\d*([.\-]|$)',
    r'(^|[.\-])mail([.\-]|$)', r'(^|[.\-])smtp([.\-]|$)', r'(^|[.\-])mx\d*([.\-]|$)',
    r'(^|[.\-])ntp([.\-]|$)', r'(^|[.\-])proxy([.\-]|$)', r'(^|[.\-])cache([.\-]|$)',
    r'(^|[.\-])sp\d+([.\-]|$)',           # e.g., sesto315-sp1-vi...
    r'(^|[.\-])ha([.\-]|$)',              # e.g., ...-ha-...
    r'(^|[.\-])gw([.\-]|$)',              # gw-eon, ibercom-gw, internap-*-gw
    r'(^|[.\-])exodus([.\-]|$)',
    r'(^|[.\-])internap([.\-]|$)',
    r'(^|[.\-])cdn([.\-]|$)',
    r'(^|[.\-])edge([.\-]|$)',
    r'(^|[.\-])akamai([.\-]|$)',
    r'(^|[.\-])fastly([.\-]|$)',
    r'(^|[.\-])cloudfront([.\-]|$)',
    r'(^|[.\-])ebs\d*([.\-]|$)',          # ebs, ebs1-...
    r'(^|[.\-])mxe\d*([.\-]|$)',          # ...-mxe001
]

# USER: unchanged (generous but sane)
USER_PATTERNS_HIGH = [
    r'(^|[.\-])cust([.\-]|$)',
    r'(^|[.\-])office([.\-]|$)',
    r'(^|[.\-])u\d+([.\-]|$)',
]
USER_PATTERNS_MED = [
    r'(^|[.\-])pppoe([.\-]|$)', r'(^|[.\-])dhcp([.\-]|$)', r'(^|[.\-])dyn(amic)?([.\-]|$)',
    r'(^|[.\-])nc-r\d+([.\-]|$)', r'(^|[.\-])nc-p\d+([.\-]|$)',
]

INFRA_HINT = re.compile(r'(^|[.\-])(tc|ta|tb|nc|na|nn|ha|sp|ec|tw)([.\-]|$)', re.IGNORECASE)

def _compile(ps): return [re.compile(p, re.IGNORECASE) for p in ps]
DNS_RES_STRICT = _compile(DNS_PATTERNS_STRICT)
DNS_RES_HINT   = _compile(DNS_PATTERNS_HINTS)
SERVER_RES     = _compile(SERVER_PATTERNS)
USER_RES_H     = _compile(USER_PATTERNS_HIGH)
USER_RES_M     = _compile(USER_PATTERNS_MED)

def _is_ip_literal(s: str) -> bool:
    try: ipaddress.ip_address(s); return True
    except Exception: return False

def _collect_names(data: dict) -> list[str]:
    names = []
    if data.get('hostname'): names.append(str(data['hostname']))
    for it in (data.get('iface_hostnames') or []):
        if it: names.append(str(it))
    nm = data.get('name')
    if nm and not _is_ip_literal(str(nm)): names.append(str(nm))
    # dedupe
    out, seen = [], set()
    for n in names:
        if n not in seen:
            out.append(n); seen.add(n)
    return out

def _first_match(names, regexes):
    for r in regexes:
        for n in names:
            if r.search(n): return n, r.pattern
    return None

def _name_has(patterns, names):
    return _first_match(names, patterns)

def _set(G, nid, role, reason, conf):
    d = G.nodes[nid]
    d['role'] = role
    d['role_reason'] = reason
    d['role_confidence'] = conf

def assign_roles(G: nx.Graph, include_external: bool = False):
    """
    Name-only classifier (no topology nudges).
    Order: DNS(strict) > DNS(hint: auth*) > SERVER > USER(high) > USER(med) > OTHER.
    """
    counts = Counter()

    for nid, data in G.nodes(data=True):
        if (not include_external) and data.get('external'):
            continue

        names = _collect_names(data)
        if not names:
            _set(G, nid, 'other', 'no hostname evidence', 'low'); counts['other'] += 1
            continue

        # DNS strict
        m = _name_has(DNS_RES_STRICT, names)
        if m:
            nm, pat = m
            _set(G, nid, 'dns', f"matched /{pat}/ in '{nm}'", 'high'); counts['dns'] += 1
            continue

        # DNS hint: auth*
        m = _name_has(DNS_RES_HINT, names)
        if m:
            nm, pat = m
            _set(G, nid, 'dns', f"hint /{pat}/ in '{nm}'", 'medium'); counts['dns'] += 1
            continue

        # SERVER (expanded)
        m = _name_has(SERVER_RES, names)
        if m:
            nm, pat = m
            _set(G, nid, 'server', f"matched /{pat}/ in '{nm}'", 'medium'); counts['server'] += 1
            continue

        # USER (high then medium)
        m = _name_has(USER_RES_H, names)
        if m:
            nm, pat = m
            _set(G, nid, 'user', f"matched /{pat}/ in '{nm}'", 'high'); counts['user'] += 1
            continue
        m = _name_has(USER_RES_M, names)
        if m:
            nm, pat = m
            _set(G, nid, 'user', f"matched /{pat}/ in '{nm}'", 'medium'); counts['user'] += 1
            continue

        # Infrastructure → other
        if any(INFRA_HINT.search(n) for n in names):
            _set(G, nid, 'other', 'router naming pattern (tc/ta/tb/nc/na/nn/ha/sp/ec/tw)', 'high'); counts['other'] += 1
            continue

        _set(G, nid, 'other', 'no explicit service/customer keywords', 'low'); counts['other'] += 1

    # final counts
    for k in ('dns','server','user','other'):
        counts.setdefault(k, 0)
    return dict(counts)
