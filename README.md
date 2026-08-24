# NDN Website-Fingerprinting Testbed

Research code accompanying the paper **“Exposing and Mitigating Website Fingerprinting Threats in Named Data Networking.”**

This repository contains the experimental testbed used to collect and process website-fingerprinting (WF) traffic in Named Data Networking (NDN). It combines browser-driven webpage replay, Mini-NDN network emulation, an ANDaNA reimplementation, packet capture and trace conversion, and trace-level WF defense simulators.

The code is a research artifact rather than a packaged application. Scripts are intended to be run from the directories shown below and several paths and dataset dimensions are configured directly in source files.

## What is included

- Construction of a Mini-NDN topology from RocketFuel ISP data.
- A pre-generated Ebone (AS 1755) Mini-NDN configuration (`experiment/1755.conf`).
- Browser-driven capture and replay of website resources using Firefox, Playwright, and HAR files.
- Website retrieval over plain NDN and an experimental ANDaNA path.
- Background traffic generation and packet capture at the target user.
- Conversion of PCAP files to timestamp/direction WF traces.
- Trace-level simulators for FRONT, WTF-PAD, Tamaraw, and RegulaTor.
- Utilities for measuring NDN communication-semantics violations in defended traces.

This snapshot does **not** include the paper's WF attack implementations, trained models, multi-tab trace generator, released datasets, VM image, or raw RocketFuel input files. The attack implementations evaluated in the paper come from their respective upstream projects.

## Repository layout

```text
.
├── experiment/
│   ├── scraper.py              # Capture live pages and save HAR/resource data
│   ├── verifyreplay.py         # Check that recorded pages can be replayed
│   ├── recordtraces.py         # Run Mini-NDN experiments and record PCAPs
│   ├── demo.py                 # Small, manually configured demonstration
│   ├── 1755.conf               # Ebone AS 1755 experiment topology
│   ├── line.conf               # Small line topology used by demo.py
│   └── util/                   # NDN, ANDaNA, HAR, logging, and traffic helpers
├── topology/
│   ├── load_rocketfuel.py      # Generate a topology from RocketFuel files
│   └── ...                     # Parsing, role assignment, and weighting helpers
└── analyze_traces/
    ├── processpcap.py          # PCAP to timestamp/direction conversion
    ├── tracemetrics.py         # NDN-semantics violation metrics
    ├── countviolations.py      # Additional violation-count utility
    └── defenses/               # FRONT, WTF-PAD, Tamaraw, and RegulaTor
```

## Environment

The collection pipeline is Linux-specific and requires root privileges because Mini-NDN/Mininet creates network namespaces and virtual interfaces. A dedicated VM is strongly recommended.

### System dependencies

- [Mini-NDN](https://github.com/named-data/mini-ndn/blob/master/docs/install.rst), including Mininet, NFD, ndn-cxx, and ndn-tools.
- `ndnputchunks` and `ndncatchunks` from ndn-tools.
- `tcpdump`, OpenSSL, `xxd`, and standard Linux process utilities.
- Firefox installed through [Playwright for Python](https://playwright.dev/python/docs/intro).
- Python 3.12 or newer for the source as written. Exact dependency versions are not pinned in this snapshot.

### Python dependencies

Install the Python packages in the same environment from which the scripts will run. If Mini-NDN and Mininet were installed as system Python packages, a virtual environment created with `--system-site-packages` may be convenient.

```bash
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install dpkt matplotlib networkx numpy pandas playwright scipy
python -m playwright install firefox
```

The experiment scripts currently set `HOME=/root`; ensure that Playwright's Firefox installation is visible in the root-run experiment environment.

## Experimental workflow

Run the collection commands from `experiment/`, because the scripts resolve `top-1m.csv`, `1755.conf`, `webpage_data/`, and `generated_traces/` relative to the current working directory.

### 1. Capture website resources

`scraper.py` visits domains from `top-1m.csv`, saves a HAR recording and extracted response bodies under `webpage_data/`, and records progress by adding columns to `top-1m.csv`.

```bash
cd experiment
python scraper.py --maxpages 100 --timeout 30000
```

This step performs active requests to public websites. Use an appropriate crawl rate and comply with applicable policies and terms.

### 2. Verify offline replay

```bash
python verifyreplay.py --maxpages 100 --timeout 30000 --numservers 20
```

Successful pages receive a server assignment (`s0` through `s19`) in `top-1m.csv`. Only pages that load and replay successfully are eligible for trace collection.

### 3. Collect PCAP traces over Mini-NDN

The supplied topology expects the following names:

- target user: `pu`
- DNS server: `dns`
- background users: `u0`, `u1`, ...
- ANDaNA relays: `r0` through `r9`
- content servers: `s0`, `s1`, ...

Run the experiment from a root-capable Python environment:

```bash
# Plain NDN with NDN-DNS and background traffic
sudo -E "$(command -v python)" recordtraces.py \
  --config 1755.conf \
  --dns \
  --bgtraffic \
  --maxpages 100 \
  --maxreplay 100
```

Add `--andana` to request page resources through two randomly selected relays. See [Known limitations](#known-limitations) before attempting this mode.

Each run creates `generated_traces/experiment_<n>/`. Website captures are stored as `<domain>.pcap`; plain-NDN runs also write per-resource statistics to `network_log.csv`.

`recordtraces.py` currently fixes the target capture interface as `pu-eth0`, starts 40 background users, and uses a 6000 ms average request interval. Change the call to `start_background_traffic(...)` when reproducing a different traffic-density setting.

## Convert PCAPs to WF traces

Run the converter from `analyze_traces/`:

```bash
cd ../analyze_traces
python processpcap.py \
  --root ../experiment/generated_traces \
  --out-dir traces \
  --target-ip 10.0.3.69
```

The output files are named `site_<i>_trace_<j>.txt`, where `<j>` is the numeric experiment directory and `<i>` is the position of the alphabetically sorted PCAP within that directory. Use `--base-increase` when combining runs copied from separate machines.

Each trace is tab-separated:

```text
0.0000	1
0.0012	-1
0.0037	-1
```

Downstream tools expect `+1` for a real outgoing packet and `-1` for a real incoming packet. Defense simulators use `+2` and `-2` for dummy packets. Before a large conversion, inspect a known capture to verify that the selected target IP and observed direction polarity match this convention.

## Defense simulators

The simulators use relative imports and should be started from their own directories. Most expect closed-world filenames of the form `site_<site>_trace_<instance>.txt`.

| Defense | Working directory | Example command |
| --- | --- | --- |
| FRONT | `analyze_traces/defenses/front` | `python main.py ../../traces -format .txt -c t1` |
| WTF-PAD | `analyze_traces/defenses/wtfpad` | `python main.py ../../traces -c normal_rcv` |
| Tamaraw | `analyze_traces/defenses/tamaraw` | `python tamaraw.py ../../traces` |
| RegulaTor | `analyze_traces/defenses/regulator` | `python regulator_sim.py ../../traces/ results/ --n_processes 8` |

FRONT, WTF-PAD, and Tamaraw create timestamped subdirectories under a local `results/` directory. Create the RegulaTor output directory before running it; its source and output path arguments should retain trailing slashes because the script concatenates filenames directly.

Dataset sizes and defense parameters are configured in the following locations:

- FRONT: `defenses/front/config.ini`
- WTF-PAD: constants at the top of `defenses/wtfpad/main.py` and distributions in `config.ini`
- Tamaraw: constants at the top of `defenses/tamaraw/tamaraw.py`
- RegulaTor: command-line options in `defenses/regulator/regulator_sim.py`

The defense directories contain the simulator sources present in this artifact. They should be treated as components used in the paper's trace-level analysis, rather than as deployable NDN defenses.

## Analyze NDN communication violations

Given a directory containing defended traces:

```bash
cd analyze_traces
python tracemetrics.py defenses/front/results/<run-directory>
python countviolations.py defenses/front/results/<run-directory>
```

`tracemetrics.py` reports three trace-level conditions used to inspect NDN compatibility: dummy data appearing before a dummy interest, more dummy interests than dummy data, and a large gap between the final positive- and negative-direction events. The timeout threshold in this snapshot is set directly in `tracemetrics.py`.

## Topology generation

The included `experiment/1755.conf` can be used directly. To regenerate it, place the required RocketFuel `.cch`, `.al`, latency, and weight files in the paths expected by `topology/load_rocketfuel.py`, then run:

```bash
cd topology
python load_rocketfuel.py
```
