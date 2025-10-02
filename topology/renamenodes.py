import networkx as nx

def rename_nodes_by_roles(G: nx.Graph, num_users: int, num_servers: int, num_relays: int, in_place: bool = True):
    """
    Rename nodes based on previously assigned node['role'] ∈ {'dns','server','user','other'}.

    Steps (in order):
      1) Pick ONE 'dns' node → name 'dns'
      2) Pick ONE 'user' node → name 'pu'   (primary user/target)
      3) Next 'user' nodes → 'u{i}' for i in [0, num_users-1]
      4) Next 'user' nodes → 'r{i}' for i in [0, num_relays-1]
      5) Next 'server' nodes → 's{i}' for i in [0, num_servers-1]
      6) All remaining nodes → 'h{i}' (i starting at 0)

    Hard fails if there aren’t enough 'dns' or 'user'/'server' nodes to satisfy the quotas.
    Nodes are only named once; leftover role-tagged nodes fall into the 'h{i}' bucket.

    Returns:
      - H: the relabeled graph (G itself if in_place=True)
      - report: dict with the chosen IDs for each category and counts
    """
    H = G if in_place else G.copy()

    # Pre-flight: gather candidates and order them deterministically by (degree asc, node-id asc)
    def _sorted(nodes):
        return sorted(nodes, key=lambda n: (H.degree(n), str(n)))

    dns_nodes    = _sorted([n for n, d in H.nodes(data=True) if d.get('role') == 'dns'])
    user_nodes   = _sorted([n for n, d in H.nodes(data=True) if d.get('role') == 'user'])
    server_nodes = _sorted([n for n, d in H.nodes(data=True) if d.get('role') == 'server'])
    # 'other' nodes will be picked up for 'h{i}' later

    # Sanity: ensure we have enough
    if not dns_nodes:
        raise RuntimeError("rename_nodes_by_roles: no node with role='dns' available.")
    need_users_total = 1 + num_users + num_relays  # +1 for 'pu'
    if len(user_nodes) < need_users_total:
        raise RuntimeError(f"rename_nodes_by_roles: need {need_users_total} 'user' nodes (incl. 'pu'), only have {len(user_nodes)}.")
    if len(server_nodes) < num_servers:
        raise RuntimeError(f"rename_nodes_by_roles: need {num_servers} 'server' nodes, only have {len(server_nodes)}.")

    # Build mapping
    mapping = {}
    assigned = set()
    report = {
        "dns": None,
        "pu": None,
        "users": [],
        "relays": [],
        "servers": [],
        "h_total": 0
    }

    # Helper to assign a single node → new_name and set a 'type' tag
    def _assign(node, new_name, type_tag):
        if new_name in H and new_name not in mapping:
            # name collision with an existing node not being relabeled
            raise RuntimeError(f"rename_nodes_by_roles: target name '{new_name}' already exists in graph.")
        if node in assigned:
            raise RuntimeError(f"rename_nodes_by_roles: node {node!r} already assigned.")
        # stamp metadata before relabel
        H.nodes[node]['orig_id'] = H.nodes[node].get('orig_id', node)
        H.nodes[node]['label'] = new_name
        H.nodes[node]['type'] = type_tag  # {'DNS','Target','user','relay','server','other'}
        assigned.add(node)
        mapping[node] = new_name

    # 1) DNS → 'dns'
    dns_node = dns_nodes[0]
    _assign(dns_node, "dns", "DNS")
    report["dns"] = dns_node

    # 2) One user → 'pu'
    pu_node = next(n for n in user_nodes if n not in assigned)
    _assign(pu_node, "pu", "Target")
    report["pu"] = pu_node

    # 3) Users → 'u{i}'
    i = 0
    users_assigned = 0
    for n in user_nodes:
        if n in assigned: 
            continue
        if users_assigned >= num_users:
            break
        _assign(n, f"u{i}", "user")
        report["users"].append(n)
        users_assigned += 1
        i += 1
    if users_assigned < num_users:
        raise RuntimeError(f"rename_nodes_by_roles: needed {num_users} additional users, assigned {users_assigned}.")

    # 4) Relays (also drawn from remaining 'user' nodes) → 'r{i}'
    i = 0
    relays_assigned = 0
    for n in user_nodes:
        if n in assigned:
            continue
        if relays_assigned >= num_relays:
            break
        _assign(n, f"r{i}", "relay")
        report["relays"].append(n)
        relays_assigned += 1
        i += 1
    if relays_assigned < num_relays:
        raise RuntimeError(f"rename_nodes_by_roles: needed {num_relays} relays, assigned {relays_assigned}.")

    # 5) Servers → 's{i}'
    i = 0
    servers_assigned = 0
    for n in server_nodes:
        if n in assigned:
            continue
        if servers_assigned >= num_servers:
            break
        _assign(n, f"s{i}", "server")
        report["servers"].append(n)
        servers_assigned += 1
        i += 1
    if servers_assigned < num_servers:
        raise RuntimeError(f"rename_nodes_by_roles: needed {num_servers} servers, assigned {servers_assigned}.")

    # 6) Everything else → 'h{i}'
    i = 0
    for n in H.nodes():
        if n in assigned:
            continue
        _assign(n, f"h{i}", "other")
        i += 1
    report["h_total"] = i

    # Finally relabel the graph
    nx.relabel_nodes(H, mapping, copy=False)

    return H, {
        **report,
        "total_renamed": len(mapping),
    }
