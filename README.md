# Artifact Appendix

Paper title: **Exposing and Mitigating Website Fingerprinting Threats in Named Data Networking**

Requested Badge(s):

- [x] **Available**
- [x] **Functional**
- [ ] **Reproduced**

## Description

This artifact accompanies:

> Michael Wrana, Anhelina Bodak, Ansh Dhingra, and Diogo Barradas. “Exposing and Mitigating Website Fingerprinting Threats in Named Data Networking.” *Proceedings on Privacy Enhancing Technologies*, accepted for 2027. The supplied accepted manuscript does not yet contain final issue or DOI metadata.

The artifact provides the collection and analysis pipeline used for the paper’s website-fingerprinting (WF) study of Named Data Networking (NDN). It contains:

- a browser-based website scraper and offline replay pipeline;
- Mini-NDN configurations for a small functional test and the paper’s 257-node, RocketFuel-derived AS 1755 topology;
- direct-NDN and experimental ANDaNA trace collection;
- PCAP-to-WF-trace conversion and single-/multi-tab dataset conversion;
- the CC-FRONT, CC-WTF-PAD, CC-Tamaraw, and CC-RegulaTor trace-level defenses;
- NDN semantic-violation checks; and
- cached intermediate results plus plotting notebooks/scripts for several paper figures and tables.

The separately released dataset contains 80,000 traces of 10,100 unique webpages. For each of four configurations—NDN/ANDaNA crossed with sparse/dense background traffic—it contains 10,000 closed-world traces (100 monitored websites visited 100 times) and 10,000 open-world traces (10,000 unmonitored websites visited once).

### Repository organization

| Path | Purpose |
|---|---|
| `experiment/` | Live capture, offline replay verification, Mini-NDN orchestration, NDN/ANDaNA helpers, background traffic, and transfer logging |
| `topology/` | Small and 257-node Mini-NDN configurations plus topology-construction helpers |
| `analyze_traces/` | PCAP-to-text conversion, attack-format conversion, and synthetic multi-tab merging |
| `defenses/` | CC-Aware defense trace transformers |
| `figures/` | CKA, feature-analysis, protocol-violation, table, and overhead scripts/data |

### Artifact workflow

| Stage | Primary program | Input | Output |
|---|---|---|---|
| Capture | `experiment/scraper.py` | `top-1m.csv` and the live web | Per-site HAR, extracted response bodies, and updated `load_result` values |
| Replay validation | `experiment/verifyreplay.py` | Captured site data | Updated `replay_result` and round-robin `server_assignment` values |
| NDN collection | `experiment/recordtraces.py` | A Mini-NDN topology plus validated captures | Per-site PCAPs and `network_log.csv` in a numbered experiment directory |
| Packet conversion | `analyze_traces/processpcap.py` | Experiment PCAP directories | `site_<i>_trace_<j>.txt` timestamp/direction traces |
| Attack conversion | `analyze_traces/convert.py` | Closed- and optionally open-world text traces | WFlib/CountMamba `.npz` data, RF-format files, or synthetic multi-tab data |
| Defense/evaluation | `defenses/` and `figures/` | Raw or defended traces and cached aggregates | CC-defended traces, semantic metrics, PDFs, and executed notebooks |

`topology/1755.conf` is the paper's pre-generated Ebone/AS 1755 topology. It contains 257 nodes and 505 links: one primary user (`pu`), 40 background users (`u0`–`u39`), 20 content servers (`s0`–`s19`), one NDN-DNS server (`dns`), ten ANDaNA relays (`r0`–`r9`), and 185 neutral forwarders. `topology/mini.conf` is the reduced functional topology.

During collection, `recordtraces.py` starts NFD on the emulated nodes, calculates link-state routes, hosts each captured resource with `ndnputchunks`, intercepts browser requests, retrieves matching chunks with `ndncatchunks`, and captures `pu-eth0`. Optional flags enable NDN-DNS, background traffic, or two-relay ANDaNA routing.


### Security/Privacy Issues and Ethical Concerns

Run the Mini-NDN collection path only in a fresh, dedicated Ubuntu virtual machine. It needs unrestricted `sudo`, creates Mininet network namespaces and virtual interfaces, runs NFD/NLSR and Open vSwitch components, captures packets, installs Python packages with `--break-system-packages`, removes Mini-NDN temporary state, and terminates `ndncatchunks`/`ndnputchunks` processes. These actions can interfere with unrelated networking or processes on a shared host.

## Basic Requirements

### Hardware Requirements

Two evaluation levels are supported.

**Released-data/trace-level functional evaluation:** A laptop or VM with 4 CPU cores, 16 GB RAM, and at least 15 GB of free disk space is sufficient. A GPU is not required for dataset validation, conversion, defenses, semantic checks, or cached-result plotting. Training the external deep-learning WF attacks may benefit from a CUDA-capable GPU, follow the guidance in linked repositories.

**Mini-NDN functional test:** Use a fresh Ubuntu 24.04 standard VM with 4 CPU cores, 16 GB RAM, and a 40 GB disk, with unrestricted `sudo`.

**Full 257-node collection:** The paper’s collection used Google Cloud `c4a-standard-16` VMs with 16 CPUs and 64 GB RAM.

### Software Requirements

The supported collection environment is Ubuntu 24.04. Python 3.12 is also required by the current source.

PyTorch, WFlib, and trained checkpoints are needed only to regenerate learned features or CKA matrices from models. They are not needed to render the cached outputs, and the model/checkpoint artifacts are not included here. WF attack implementations and their own dependencies are external, as listed in [Experiment 3](#experiment-3-format-traces-and-run-wf-attacks).

The released dataset is documented in [Accessibility](#accessibility) and [Set Up the Environment](#set-up-the-environment).

### Estimated Time and Storage Consumption

Times below are approximate and depend on network speed and hardware.

| Activity | Human-time | Compute-time | Disk space |
|---|---:|---:|---:|
| Clone, Python environment, and dataset download/extraction | 20 min | 60 min | 10 GB |
| Dataset integrity and small conversion smoke test | 5 min | 5 min | 1 GB |
| Convert one complete configuration to attack formats | 2 min | 60 min | 10 GB |
| Apply one CC defense to 10,000 monitored traces | 5 min | 2 hours | 25 GB |
| Render figures | 5 min | 10 min | negligible |
| Install Mini-NDN from source | 20 min | 1 hour | 15 GB |
| Single-site scrape test | 1 min | 1 min | 1 GB |
| Single-site Mini-NDN PCAP test | 1 min | 5 min | 1 GB |
| Full live website capture | 1 min | 320 hours | 500 GB |
| Full collection reported in the paper | 1 min | 500 hours | 2 TB |


## Environment

### Accessibility

Code:

- Repository: [https://github.com/MichaelWrana/mnndn-scripts-new](https://github.com/MichaelWrana/mnndn-scripts-new)


Dataset:

- Landing page: [NDN datasets](https://nextcloud.cs.uwaterloo.ca/s/sadrgRWEeTQN3a8)
- Direct archive: [ndn_datasets.tar.bz2](https://nextcloud.cs.uwaterloo.ca/s/sadrgRWEeTQN3a8/download)
- Archive size: 555,529,730 bytes (about 530 MiB)
- SHA-256: `05b27dd29ef1808eab3b6ccdff938324303ebf7bc63225648e12d4c229ae3819`
- Extracted payload: 80,000 trace files, about 6.9 GB on disk


### Set Up the Environment

#### Path A: released-data and trace-level evaluation

On Ubuntu 24.04 or another recent Linux distribution:

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates python3-full python3-pip
git clone https://github.com/MichaelWrana/mnndn-scripts-new.git
cd mnndn-scripts-new

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy pandas scipy matplotlib tqdm dpkt networkx jupyter
```

Keep reusable paths before changing directories:

```bash
ARTIFACT_ROOT="$(pwd)"
DATASET_ROOT="$ARTIFACT_ROOT/datasets"
export ARTIFACT_ROOT DATASET_ROOT
```

Download and verify the released dataset:

```bash
mkdir -p "$DATASET_ROOT"
curl -L \
  https://nextcloud.cs.uwaterloo.ca/s/sadrgRWEeTQN3a8/download \
  -o "$ARTIFACT_ROOT/ndn_datasets.tar.bz2"

echo "05b27dd29ef1808eab3b6ccdff938324303ebf7bc63225648e12d4c229ae3819  $ARTIFACT_ROOT/ndn_datasets.tar.bz2" \
  | sha256sum -c -

tar --warning=no-unknown-keyword -xjf \
  "$ARTIFACT_ROOT/ndn_datasets.tar.bz2" \
  -C "$DATASET_ROOT"
```

Some tar versions report harmless unknown extended-attribute warnings originating from macOS quarantine metadata. `--warning=no-unknown-keyword` suppresses warnings.
The extracted directory should contain:

```text
datasets/
├── andana_dense_nodef_cw_1tab/
├── andana_dense_nodef_ow_1tab/
├── andana_sparse_nodef_cw_1tab/
├── andana_sparse_nodef_ow_1tab/
├── ndn_dense_nodef_cw_1tab/
├── ndn_dense_nodef_ow_1tab/
├── ndn_sparse_nodef_cw_1tab/
└── ndn_sparse_nodef_ow_1tab/
```

Each closed-world (`cw`) directory contains `site_0_trace_0.txt` through the 100-by-100 monitored set. Each open-world (`ow`) directory contains `site_0.txt` through `site_9999.txt`.

#### Path B: Mini-NDN collection environment

Begin with a fresh Ubuntu 24.04 VM with at least 4 cores, 16 GB RAM, and 40 GB disk space, and unrestricted `sudo`. A dedicated VM is **VERY STRONGLY** recommended.

Optional warm-up:

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo reboot
```

After reconnecting, install system and Python packages:

```bash
sudo apt-get install -y \
  git curl ca-certificates build-essential \
  python3-full python3-dev python3-pip python3-setuptools \
  python3-packaging python3-pexpect \
  python3-igraph python3-joblib python3-tqdm \
  python3-pandas python3-numpy \
  openssl xxd tcpdump tshark
```

When `tshark` asks whether non-superusers should be able to capture packets, choose **Yes**, then reboot:

```bash
sudo reboot
```

Install Mini-NDN in this exact order:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/ndn-wf
cd /opt/ndn-wf
git clone https://github.com/named-data/mini-ndn.git
cd mini-ndn
git checkout --detach 73add71f860979426aef63136bf78ed525862e5c

./install.sh --source --release=2024-08 --no-wifi --jobs=4 --dl-only -y
git -C dl/mininet fetch origin refs/pull/1247/head
git -C dl/mininet checkout --detach 388483bb9ade1dbe118dd05a7c8419ae8888367e

set -o pipefail
./install.sh --source --release=2024-08 --no-wifi --jobs=4 -y \
  2>&1 | tee "$HOME/mini-ndn-install.log"

sudo python3 -m pip install --break-system-packages \
  --editable /opt/ndn-wf/mini-ndn
sudo sh -c 'echo /usr/local/lib64 > /etc/ld.so.conf.d/ndn-local.conf'
sudo ldconfig
```

The installer may report errors from ancient/defunct OpenFlow commands. Continue to the verification checks.

Verify executables and basic Mininet operation:

```bash
command -v mn
command -v mnexec
command -v ovs-vsctl
command -v ofdatapath
command -v nfd
command -v nlsr
command -v ndnputchunks
command -v ndncatchunks

sudo mn -c
sudo mn --test pingall
```

The executable paths should include `/usr/local/bin/mn`, `/usr/bin/mnexec`, `/usr/bin/ovs-vsctl`, `/usr/local/bin/nfd`, `/usr/local/bin/nlsr`, `/usr/local/bin/ndnputchunks`, and `/usr/local/bin/ndncatchunks`. The Mininet test should finish with `0% dropped (2/2 received)`.

Verify Python imports:

```bash
sudo python3 - <<'PY'
import igraph
import mininet
import minindn
print("Python imports OK")
PY
```

Expected output:

```text
Python imports OK
```

From `/opt/ndn-wf/mini-ndn`, start the interactive example:

```bash
sudo python3 examples/mnndn.py \
  /opt/ndn-wf/mini-ndn/topologies/default-topology.conf
```

Expected behavior is a four-node topology (`a b c d`), NFD and NLSR startup, and a `mini-ndn>` prompt. Exit with `Ctrl-D`, clean up, and run the routing test:

```bash
sudo mn -c
sudo python3 examples/nlsr/pingall.py \
  /opt/ndn-wf/mini-ndn/topologies/default-topology.conf
```

After approximately 60 seconds, the output should say `NLSR has converged successfully` and schedule pings among all four nodes. Stop with `Ctrl-C`, then clean up:

```bash
sudo mn -c
```

Install the browser tooling and artifact:

```bash
sudo python3 -m pip install --break-system-packages "playwright==1.61.0"
sudo env HOME=/root python3 -m playwright install --with-deps firefox

cd /opt/ndn-wf
git clone https://github.com/MichaelWrana/mnndn-scripts-new.git
cd /opt/ndn-wf/mnndn-scripts-new

cp -v topology/mini.conf experiment/mini.conf
sudo mn -c
```

For the full 257-node commands, also copy the included topology to the working directory expected by `recordtraces.py`:

```bash
cp -v topology/1755.conf experiment/1755.conf
```

### Testing the Environment

#### Released-data checks

Activate the virtual environment and move to the repository root:

```bash
cd /path/to/mnndn-scripts-new
source .venv/bin/activate
```

Check syntax and imports:

```bash
python -m compileall -q analyze_traces defenses figures topology
python - <<'PY'
import dpkt
import matplotlib
import networkx
import numpy
import pandas
import scipy
import tqdm
print("Analysis imports OK")
PY
```

Expected output is `Analysis imports OK`, with no output from `compileall`.

Verify archive contents:

```bash
find datasets -mindepth 1 -maxdepth 1 -type d | sort
find datasets -mindepth 2 -maxdepth 2 -type f | wc -l
wc -l datasets/andana_dense_nodef_cw_1tab/site_0_trace_0.txt
head -n 5 datasets/andana_dense_nodef_cw_1tab/site_0_trace_0.txt
```

The first command should list the eight directories shown above and the second should print `80000`. The final command should show two tab-separated fields per line: a nonnegative relative timestamp and a direction such as `1` or `-1`.

Run a four-trace conversion test:

```bash
mkdir -p formatted_traces
cd analyze_traces
python convert.py \
  --tracescw ../datasets/andana_dense_nodef_cw_1tab \
  --outdir ../formatted_traces \
  --sites 2 \
  --exp 2

cd ..
python - <<'PY'
import numpy as np
p = "formatted_traces/andana_dense_nodef_cw_1tab_wflib.npz"
d = np.load(p)
print(d["X"].shape, d["y"].shape)
assert d["X"].shape == (4, 5000)
assert d["y"].shape == (4,)
print("Trace conversion OK")
PY
```

Expected final output is `Trace conversion OK`.

#### End-to-end Mini-NDN test

First capture the first accessible website from `experiment/top-1m.csv`:

```bash
cd /opt/ndn-wf/mnndn-scripts-new/experiment
sudo env HOME=/root python3 -u scraper.py \
  --maxpages 1 \
  --timeout 60000
```

The seed CSV is a ranked Tranco list. The first entry is normally `google.com`. Because this step accesses the live web, the exact first successful site and captured resources can change.

Verify its offline replay and collect one PCAP on the small topology:

```bash
cd /opt/ndn-wf/mnndn-scripts-new/experiment
sudo env HOME=/root python3 -u verifyreplay.py \
  --maxpages 1 \
  --timeout 60000
sudo env HOME=/root python3 -u recordtraces.py \
  --config mini.conf \
  --maxpages 1 \
  --maxreplay 1 \
  --timeout 120000 \
  --overwrite
```

Expected output is a new directory such as `generated_traces/experiment_0/` containing one site PCAP (normally `google.com.pcap`) and `network_log.csv`.

Inspect it:

```bash
sudo tcpdump -nn \
  -r generated_traces/experiment_0/google.com.pcap \
  -c 10
sudo tcpdump -nn \
  -r generated_traces/experiment_0/google.com.pcap \
  2>/dev/null | wc -l
cat generated_traces/experiment_0/network_log.csv
```

If the selected successful site is not `google.com`, substitute the PCAP filename printed by the collection script. A nonempty packet listing and transfer log demonstrate browser capture, replay, NDN routing, content retrieval, and target-interface recording.

Optionally convert the mini-topology PCAP. The target user in `mini.conf` normally receives `10.0.0.1`:

```bash
cd /opt/ndn-wf/mnndn-scripts-new/analyze_traces
python3 processpcap.py \
  --root ../experiment/generated_traces \
  --target-ip 10.0.0.1 \
  --out-dir ../mini_text_traces

head ../mini_text_traces/site_0_trace_0.txt
```

The output should again be a tab-separated timestamp/direction trace.

## Artifact Evaluation

### Main Results and Claims

#### Main Result 1: A reusable large-scale NDN WF testbed and dataset

The artifact implements live capture, deterministic offline replay, NDN/ANDaNA retrieval, background traffic, packet capture, and trace conversion. The paper uses it to collect 80,000 page loads for 10,100 unique webpages over four configurations on a 257-node topology (Sections 3 and 5.1). [Experiment 1](#experiment-1-validate-the-released-dataset) validates the released corpus, while [Experiment 2](#experiment-2-run-the-ndn-collection-pipeline) exercises the pipeline end to end at reduced scale.

#### Main Result 2: TCP/IP WF attacks remain highly effective on NDN and ANDaNA

Across the undefended configurations, the paper reports 97.9%–99.8% single-tab accuracy and 81.2%–97.0% three-tab P@3, depending on attack and configuration (Table 2, Section 6.1). [Experiment 3](#experiment-3-format-traces-and-run-wf-attacks) prepares the exact released traces for the external attack implementations.

#### Main Result 3: NDN models learn a different representation from TCP/IP models

Feature analysis indicates increased reliance on timing features in NDN, and Tik-Tok CKA shows strong within-NDN alignment but almost no NDN-to-TCP/IP alignment. [Experiment 5](#experiment-5-render-cached-figures-and-tables) renders the supplied matrices and feature summaries.

#### Main Result 4: CC-aware defenses

[Experiment 4](#experiment-4-apply-cc-defenses-and-check-ndn-semantics) produces attack-ready defended traces, [Experiment 3](#experiment-3-format-traces-and-run-wf-attacks) points to the attack evaluators, and [Experiment 5](#experiment-5-render-cached-figures-and-tables) renders the papers' results using cached data.

### Experiments

#### Experiment 1: Validate the released dataset

From the repository root with Path A configured:

```bash
echo "05b27dd29ef1808eab3b6ccdff938324303ebf7bc63225648e12d4c229ae3819  ndn_datasets.tar.bz2" \
  | sha256sum -c -

test "$(find datasets -mindepth 2 -maxdepth 2 -type f | wc -l)" -eq 80000

for d in datasets/*_cw_1tab; do
  printf "%s: " "$d"
  find "$d" -maxdepth 1 -type f | wc -l
done

for d in datasets/*_ow_1tab; do
  printf "%s: " "$d"
  find "$d" -maxdepth 1 -type f | wc -l
done
```

Expected results:

- checksum status `OK`;
- 80,000 total files;
- 10,000 files in each of four closed-world directories; and
- 10,000 files in each of four open-world directories.


#### Experiment 2: Run the NDN collection pipeline

Run the [end-to-end Mini-NDN functional test](#end-to-end-mini-ndn-functional-test). The resulting PCAP, `network_log.csv`, and converted text trace demonstrate that the main components work together.

For future full-scale collection, capture live content:

```bash
cd /opt/ndn-wf/mnndn-scripts-new/experiment
sudo env HOME=/root python3 -u scraper.py \
  --maxpages 100 \
  --timeout 60000
sudo env HOME=/root python3 -u scraper.py \
  --maxpages 10100 \
  --timeout 60000
```


`recordtraces.py` only accepts rows that passed offline replay. Verify the complete captured set before collection:

```bash
sudo env HOME=/root python3 -u verifyreplay.py \
  --maxpages 10100 \
  --timeout 60000
```

Then run the four supplied dataset collections (closed/open world for direct NDN and ANDaNA):

```bash
sudo env HOME=/root python3 -u recordtraces.py \
  --config 1755.conf \
  --maxpages 100 \
  --maxreplay 100 \
  --timeout 120000 \
  --dns \
  --bgtraffic \
  --overwrite

sudo env HOME=/root python3 -u recordtraces.py \
  --config 1755.conf \
  --maxpages 10000 \
  --maxreplay 1 \
  --timeout 120000 \
  --dns \
  --bgtraffic \
  --overwrite

sudo env HOME=/root python3 -u recordtraces.py \
  --config 1755.conf \
  --maxpages 100 \
  --maxreplay 100 \
  --timeout 120000 \
  --dns \
  --bgtraffic \
  --andana \
  --overwrite

sudo env HOME=/root python3 -u recordtraces.py \
  --config 1755.conf \
  --maxpages 10000 \
  --maxreplay 1 \
  --timeout 120000 \
  --dns \
  --bgtraffic \
  --andana \
  --overwrite
```

One invocation visits each eligible site at most once. Recording 100 monitored samples per site requires repeated calls (or coordinated VMs) while preserving/incrementing `replay_count`.  Use `--overwrite` only on the initial run because it resets that column. Keep direct-NDN and ANDaNA outputs in separate locations before changing configurations.

`recordtraces.py` passes `avg_interval_ms=6000` to the background-traffic generator, whose uniform multiplier of 0.5–1.5 produces the paper's sparse 3000–9000 ms interval. The paper's dense 500–1500 ms interval corresponds to `avg_interval_ms=1000`.

For the 257-node topology, `processpcap.py` defaults to target IP `10.0.3.69`:

```bash
cd /opt/ndn-wf/mnndn-scripts-new/analyze_traces
python3 processpcap.py \
  --root ../experiment/generated_traces \
  --target-ip 10.0.3.69 \
  --out-dir ../full_text_traces
```

#### Experiment 3: Format traces and run WF attacks

The paper’s main dense-ANDaNA single-tab input can be converted from the released data as follows:

```bash
cd /path/to/mnndn-scripts-new
source .venv/bin/activate
mkdir -p formatted_traces

cd analyze_traces
python convert.py \
  --tracescw ../datasets/andana_dense_nodef_cw_1tab \
  --tracesow ../datasets/andana_dense_nodef_ow_1tab \
  --outdir ../formatted_traces \
  --sites 100 \
  --exp 100 \
  --numopen 10000
```

This produces WFlib and CountMamba `.npz` files and an RF directory based on the open-world input name. For the paper’s three-tab setting:

```bash
python convert.py \
  --tracescw ../datasets/andana_dense_nodef_cw_1tab \
  --tracesow ../datasets/andana_dense_nodef_ow_1tab \
  --outdir ../formatted_traces \
  --sites 100 \
  --exp 100 \
  --numopen 10000 \
  --numtabs 3 \
  --nummulti 50000
```

The multi-tab generator randomly selects and overlaps independently collected traces.

If you wish to evaluate WF attack performance, use the following implementations and follow the instructions in each repository.

- [k-Fingerprinting](https://github.com/jhayes14/k-FP)
- [DF, Tik-Tok, BAPM, ARES, and TMWF via WFlib](https://github.com/FIND-Lab/Website-Fingerprinting-Library)
- [Robust Fingerprinting](https://github.com/robust-fingerprinting/RF)
- [CountMamba](https://github.com/SJTU-dxw/CountMamba-WF)


#### Experiment 4: Apply CC defenses


The paper’s principal defense evaluation uses dense ANDaNA closed-world traces:

```bash
cd /path/to/mnndn-scripts-new
source .venv/bin/activate
ARTIFACT_ROOT="$(pwd)"
DATASET_ROOT="$ARTIFACT_ROOT/datasets"
export ARTIFACT_ROOT DATASET_ROOT
```

**CC-Tamaraw**

```bash
cd "$ARTIFACT_ROOT/defenses/cc-tamaraw"
python cc_tamaraw.py \
  "$DATASET_ROOT/andana_dense_nodef_cw_1tab"
```

The output is a timestamped directory under `results/` containing `site_<site>_trace_<instance>.txt` files and one pickle-backed `.npz` file per website.

**CC-WTF-PAD**

```bash
cd "$ARTIFACT_ROOT/defenses/cc-wtfpad"
python cc-wtfpad.py \
  "$DATASET_ROOT/andana_dense_nodef_cw_1tab" \
  -c normal_rcv
```

The output is a timestamped `results/wtfpad_<timestamp>/` directory containing defended text traces and per-site pickle-backed `.npz` files.

**CC-RegulaTor**

The output directory must already exist and the source/output arguments should include trailing slashes:

```bash
cd "$ARTIFACT_ROOT/defenses/cc-regulator"
mkdir -p results/andana_dense
python cc_regulator.py \
  "$DATASET_ROOT/andana_dense_nodef_cw_1tab/" \
  "results/andana_dense/" \
  --n_processes 4
```

This writes defended text traces, aggregate pickle data, and per-site `website_<site>_processed.npz` pickle files.

**CC-FRONT**

CC-FRONT expects one pickle-backed file named `website_<site>_processed.npz` per monitored site.

```bash
cd "$ARTIFACT_ROOT/defenses/cc-front"
mkdir -p input_andana_dense

python - "$DATASET_ROOT/andana_dense_nodef_cw_1tab" input_andana_dense <<'PY'
from pathlib import Path
import pickle
import sys
import numpy as np

source = Path(sys.argv[1])
target = Path(sys.argv[2])
target.mkdir(parents=True, exist_ok=True)

for site in range(100):
    traces = []
    for instance in range(100):
        path = source / f"site_{site}_trace_{instance}.txt"
        trace = np.loadtxt(path, delimiter="\t")
        signed = np.copysign(trace[:, 0], trace[:, 1])
        traces.append(signed)
    with (target / f"website_{site}_processed.npz").open("wb") as out:
        pickle.dump({site: traces}, out)
print("Prepared 100 CC-FRONT input files")
PY

python cc_front.py input_andana_dense -c t1
```

The output is a timestamped `results/cc_front<timestamp>/` directory with defended text traces and per-site pickle-backed outputs.


The original TCP/IP-oriented defense implementations used for comparison are external. Follow their own instructions:

- [FRONT](https://github.com/websitefingerprinting/WebsiteFingerprinting)
- [WTF-PAD](https://github.com/wtfpad/wtfpad)
- [RegulaTor](https://github.com/jkhollandjr/RegulaTor)
- [Tamaraw](https://github.com/websitefingerprinting/wfdef)

Convert the CC-defended outputs with `analyze_traces/convert.py` and evaluate them using the attack repositories from Experiment 3.

#### Experiment 5: Render figures and tables

The repository includes cached CKA matrices. Render all three Figure 4 panels:

```bash
cd /path/to/mnndn-scripts-new
source .venv/bin/activate
mkdir -p rendered_figures

python figures/cka_heatmaps/visualizecka.py \
  --cka_file figures/cka_heatmaps/cka_data/ndn_only.npz \
  --out_file rendered_figures/cka_ndn_only.pdf \
  --title "NDN Only"

python figures/cka_heatmaps/visualizecka.py \
  --cka_file figures/cka_heatmaps/cka_data/tcpip_only.npz \
  --out_file rendered_figures/cka_tcpip_only.pdf \
  --title "TCP/IP Only"

python figures/cka_heatmaps/visualizecka.py \
  --cka_file figures/cka_heatmaps/cka_data/ndn_vs_tcpip.npz \
  --out_file rendered_figures/cka_ndn_vs_tcpip.pdf \
  --title "NDN vs TCP/IP"
```

Render the feature summaries and k-Fingerprinting comparison:

```bash
python figures/feature_analysis/visualizedataset.py \
  --in_dir figures/feature_analysis/andana_dense_nodef_cw_1tab_wflib \
  --out_dir rendered_figures

cd figures/feature_analysis
python visualizekfp.py
mv kfp_feature_importance.pdf ../../rendered_figures/
cd ../..
```

Expected files include `embedding_spread_vs_neighbor_distance.pdf`, `top_soft_confusion_edges.pdf`, and `kfp_feature_importance.pdf`.

Execute the cached protocol-violation and table/overhead notebooks:

```bash
cd figures/protocol_violations
jupyter nbconvert \
  --to notebook \
  --execute single_protocol_violations.ipynb \
  --output single_protocol_violations.executed.ipynb

cd ../tables_and_overheads
jupyter nbconvert \
  --to notebook \
  --execute tables_and_overheads.ipynb \
  --output tables_and_overheads.executed.ipynb
```

The first notebook uses the included `unsolicited-data.txt` and `unsatisfied-interest.txt` aggregates and writes `unsolicited-data.pdf`. The second embeds cached aggregate attack/overhead values and writes six table PDFs covering FRONT, WTF-PAD, and RegulaTor in one- and three-tab settings.



### Scope and Known Limitations

This submission requests **Available** and **Functional**, not **Reproduced**.

- The repository does not include raw HAR captures, trained attack checkpoints, per-run attack outputs, or train/test split manifests.
- Randomized multi-tab merging and defense simulators do not use a fixed experiment seed, so outputs are not byte-for-byte deterministic.
- `topology/1755.conf` is included, but the raw RocketFuel ISP maps must be downloaded from their website.
- CC-FRONT’s `.npz` input layout is not generated by a repository utility, but the conversion step above supplies the missing preparation step.


These limitations do not prevent the reduced Mini-NDN test, released-dataset processing, CC-defense execution, or cached-result rendering required to establish artifact functionality.

## Reusability

The artifact can be reused to:

- collect NDN traffic for an arbitrary domain list by replacing `experiment/top-1m.csv`.
- vary topology, DNS use, background traffic, and ANDaNA routing through `recordtraces.py` options.
- merge independently collected traces into single-tab and multi-tab workloads with `analyze_traces/convert.py`.
- Export WFlib, CountMamba, and RF-compatible datasets.
- Develop new content-centric defenses based on the provided CC-defense implementations or apply CC-defenses to other WF datasets.
