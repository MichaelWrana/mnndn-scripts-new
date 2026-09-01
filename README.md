# NDN Website-Fingerprinting Research Artifact

Research code accompanying the paper **“Exposing and Mitigating Website Fingerprinting Threats in Named Data Networking.”**

This repository contains the collection and analysis pipeline used to study website fingerprinting (WF) in Named Data Networking (NDN). It combines browser-based webpage capture and replay, a 257-node Mini-NDN topology, plain-NDN and experimental ANDaNA retrieval, packet-to-trace conversion, trace-level congestion-control defense variants, and scripts used to produce several paper figures and tables.

## Repository layout

```text
.
├── analyze_traces/
│   ├── processpcap.py          # Convert target-user PCAPs to WF traces
│   ├── convert.py              # Reformat and merge traces for attack toolkits
│   └── util/                   # Trace loading and multi-tab processing helpers
├── defenses/
│   ├── cc-front/               # Congestion-control FRONT variant and evaluator
│   ├── cc-regulator/           # Congestion-control RegulaTor variant
│   ├── cc-tamaraw/             # Congestion-control Tamaraw variant and baseline
│   └── cc-wtfpad/              # Congestion-control WTF-PAD implementation
├── experiment/
│   ├── scraper.py              # Record live pages as HAR files and resources
│   ├── verifyreplay.py         # Validate offline replay and assign NDN servers
│   ├── recordtraces.py         # Orchestrate Mini-NDN collection experiments
│   ├── logmetrics.py           # Summarize ndncatchunks transfer measurements
│   ├── ow.sh / ow-clean.sh     # Open-world batch/cleanup helpers
│   ├── top-1m.csv              # Ranked domain seed list
│   └── util/                   # ANDaNA, NDN, HAR, DNS, and traffic helpers
├── figures/
│   ├── cka_heatmaps/           # CKA extraction, saved matrices, and heatmaps
│   ├── feature_analysis/       # Feature extraction/visualization scripts
│   ├── protocol_violations/    # NDN-semantics violation plots and source data
│   └── tables_and_overheads/   # Notebook for reported tables and overheads
└── topology/
    ├── 1755.conf               # Pre-generated Ebone (AS 1755) topology
    └── *.py                    # RocketFuel parsing, weighting, and role assignment
```

## Code overview

### Topology construction

`topology/` turns RocketFuel ISP maps and link-weight/latency data into a Mini-NDN configuration. The helpers load the graph, compute edge weights, rename nodes, and assign the experiment roles described in the paper. The included `1755.conf` contains 257 nodes: one target user (`pu`), 40 background users (`u0`–`u39`), 20 content servers (`s0`–`s19`), one NDN-DNS server (`dns`), 10 ANDaNA relays (`r0`–`r9`), and 185 neutral forwarders (`h*`). Raw RocketFuel inputs are not included.

### Website capture and NDN experiments

`experiment/scraper.py` visits domains from `top-1m.csv`, records each page as a HAR archive, and extracts response bodies for later replay. `verifyreplay.py` checks that the captured page can be served offline and records a content-server assignment.

`recordtraces.py` coordinates the Mini-NDN experiment: it loads the topology, starts NFD routing, hosts captured resources, generates background traffic, replays a page in the browser, and records the target-user interface with `tcpdump`. It supports direct NDN retrieval and the paper's experimental ANDaNA mode. The ANDaNA helpers in `experiment/util/andana.py` establish X25519/HKDF-derived host–relay keys and onion-wrap Interests and returned Data across two relays selected from the ten-relay pool. The remaining files in `experiment/util/` provide NDN transfer, HAR matching, NDN-DNS, background-traffic, and process-management helpers.

### Trace processing

`analyze_traces/processpcap.py` extracts packet timestamps and directions from experiment PCAPs. `analyze_traces/convert.py` and `analyze_traces/util/` load those traces, synthesize multi-tab overlaps, and emit formats expected by WFlib, CountMamba, and RF-style evaluation code.

The downstream analysis and defense code uses tab-separated events with the following direction convention:

- `+1`: real outgoing Interest
- `-1`: real incoming Data
- `+2`: dummy outgoing Interest
- `-2`: dummy incoming Data


### Congestion-control defense variants

`defenses/` contains the four trace-level congestion-control (CC) variants evaluated in the paper:

- **CC-FRONT** adapts FRONT's random padding schedule and includes an evaluation helper.
- **CC-WTF-PAD** applies adaptive-padding histograms while tracking NDN Interest/Data constraints.
- **CC-Tamaraw** adapts Tamaraw's fixed-rate padding and also retains a local baseline Tamaraw script.
- **CC-RegulaTor** adapts RegulaTor's burst and padding schedule to the CC setting.


### Figure and table generation

The exact figures shown in the paper can be generated from the scripts here.  We use cached outputs from the WF attacks and defenses.  If you want to generate them from scratch yourself, see [WF attacks](###-WF-attacks), [WF defenses](###-WF-defenses), and [dataset](###-Dataset)

`figures/cka_heatmaps/` stores CKA matrices and scripts for layer-similarity heatmaps. `figures/feature_analysis/` extracts and visualizes learned and k-Fingerprinting-style features. `figures/protocol_violations/` contains the plotting code and aggregate inputs for the NDN communication-semantics analysis. `figures/tables_and_overheads/` contains the notebook used for reported tables and overhead calculations.


## NDN simulation setup

> **Status:** Detailed setup and execution instructions are forthcoming. The Mini-NDN collection environment has several system-level dependencies, so this section will be completed after a reproducible distribution format (for example, a container or VM image) is selected.

## Not included in this repository

### WF attacks

We use existing open-source implementations of the following WF attacks in the paper.

* k-Fingerprinting: [code](https://github.com/jhayes14/k-FP)
* Deep Fingerprinting: [code](https://github.com/FIND-Lab/Website-Fingerprinting-Library)
* Tik-Tok: [code](https://github.com/FIND-Lab/Website-Fingerprinting-Library)
* BAPM: [code](https://github.com/FIND-Lab/Website-Fingerprinting-Library)
* ARES: [code](https://github.com/FIND-Lab/Website-Fingerprinting-Library)
* TMWF: [code](https://github.com/FIND-Lab/Website-Fingerprinting-Library)
* Robust Fingerprinting: [code](https://github.com/robust-fingerprinting/RF)
* CountMamba: [code](https://github.com/SJTU-dxw/CountMamba-WF)

### WF defenses

We use existing open-source implementations of the following WF defenses in the paper.

* FRONT: [code](https://github.com/websitefingerprinting/WebsiteFingerprinting)
* WTF-PAD: [code](https://github.com/wtfpad/wtfpad)
* RegulaTor: [code](https://github.com/jkhollandjr/RegulaTor)
* Tamaraw: [code](https://github.com/websitefingerprinting/wfdef)


### Dataset

The complete NDN, ANDaNA, open-world, and closed-world datasets used in the paper's evaluation containing 80,000 traces of 10,100 websites can be downloaded here: [dataset](https://nextcloud.cs.uwaterloo.ca/s/sadrgRWEeTQN3a8)