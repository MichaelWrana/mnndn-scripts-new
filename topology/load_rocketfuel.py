import re
import ipaddress
import networkx as nx
from collections.abc import Set as AbcSet
from math import ceil

from loadcch import *
from computeweights import *
from assignroles import *
from renamenodes import *

def prune_leaf_others(G: nx.Graph, keep_roles={'dns','server','user'}, iterative=True):
    """
    Remove nodes with degree==1 whose node['role'] not in keep_roles.
    Returns the total number of nodes removed.
    """
    removed_total = 0
    while True:
        to_drop = [n for n, d in G.degree()
                   if d == 1 and G.nodes[n].get('role') not in keep_roles]
        if not to_drop:
            break
        G.remove_nodes_from(to_drop)
        removed_total += len(to_drop)
        if not iterative:
            break
    return removed_total

# ---- example quick test (paste your snippet to a temp file and run) ----
if __name__ == "__main__":
    network = "1755"

    G, rep = build_graph_from_cch_al(f"rocketfuel_maps_cch/{network}.cch", f"rocketfuel_maps_cch/{network}.al", keep_stubs=False)
    print(f"{rep}\n\n")
    print(f"Raw Network: |V|={G.number_of_nodes()}  |E|={G.number_of_edges()}")

    G.remove_nodes_from([node for node in G.nodes if node<0])
    G.remove_nodes_from(list(nx.isolates(G)))

    print(f"Pruned Stubs and Isolates: |V|={G.number_of_nodes()}  |E|={G.number_of_edges()}\n\n")

    rep = load_location_data_into_graph(
        G,
        f"weights-dist/{network}/latencies.intra",
        attr="delay",           # or "latency_ms"
        also_set_weight=False,   # mirror into edge['weight'] for nx algorithms
        include_external=False, # stick to intra-ISP nodes
        aggregator="min"        # collapse duplicate lines per location-pair
    )
    print(f"{rep}\n\n")

    rep = load_location_data_into_graph(
        G,
        f"weights-dist/{network}/weights.intra",
        attr="weight",           # or "latency_ms"
        also_set_weight=False,   # mirror into edge['weight'] for nx algorithms
        include_external=False, # stick to intra-ISP nodes
        aggregator="min"        # collapse duplicate lines per location-pair
    )
    print(f"{rep}\n\n")

    rep = assign_roles(G, include_external=False)
    print(f"{rep}\n\n") 

    #G = prune_to_spanning_tree(G)

    removed = prune_leaf_others(G)   
    print(f"No Leaves: |V|={G.number_of_nodes()}  |E|={G.number_of_edges()}")

    G, rep = rename_nodes_by_roles(G, num_users=40, num_servers=20, num_relays=10)
    print(f"{rep}\n\n")

    i = rep["h_total"]
    j = 0
    mapping = {}
    nodes_to_add = []
    edges_to_add = []
    for node,data in G.nodes(data=True):
        if data['type'] == "server" or data["type"] == "relay" or data["type"] == "user":
            if G.degree(node) > 1: # rework node and attach to make the servers/users actual endpoints
                new_node_id = "n" + str(j)
                nodes_to_add.append([new_node_id, data["role"], data["label"], data["type"]])
                edges_to_add.append([new_node_id, node, 1.0, 1.0])
                mapping[node] = "h" + str(i)
                mapping[new_node_id] = node
                data["type"] = "other"
                data["label"] = mapping[node]
                i+=1
                j+=1

    for node in nodes_to_add:
        G.add_node(node[0], role=node[1], label=node[2], type=node[3])
    
    for edge in edges_to_add:
        G.add_edge(edge[0], edge[1], delay=edge[2], weight=edge[3])

    G = nx.relabel_nodes(G, mapping, copy=False)
    
    # nodes
    for _, data in G.nodes(data=True):
        for k, v in list(data.items()):
            if isinstance(v, (AbcSet, set)) or isinstance(v, type) or v is None or k == "name":
                del data[k]

    # edges
    for _, _, data in G.edges(data=True):
        for k, v in list(data.items()):
            if isinstance(v, (AbcSet, set)) or isinstance(v, type) or v is None or k == "name":
                del data[k]

    # also clean graph-level attrs
    for k, v in list(G.graph.items()):
        if isinstance(v, (AbcSet, set)) or isinstance(v, type) or v is None or k == "name":
            del G.graph[k]
    
    nx.write_graphml(G, f"{network}.graphml")

    with open(f"{network}.conf", "w") as f:
        f.write("[nodes]\n")
        for node in G.nodes():
            f.write(f"{node}\n")

        f.write("[links]\n")
        for u,v,data in G.edges(data=True):
            if u == v:
                continue
            try:
                delay=data["delay"]
                weight=data["weight"]
                du = G.degree(u)
                dv = G.degree(v)
                max_queue_size = 15 + 2 * (du + dv)
                bw = 10 + ceil(0.5 * (du + dv))
            except KeyError:
                delay=1
                weight=1
                max_queue_size=25
                bw=10
            f.write(f"{u}:{v} delay={int(delay)}ms\n")
            #f.write(f"{u}:{v} delay={int(delay)}ms weight={int(weight)} use_htb=1\n")

        
