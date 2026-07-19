# Mixed Python + React Uni-Agent/veRL example

For a Colab A100 run where coding commands intentionally execute in the same
VM as the model, see [COLAB_A100.md](COLAB_A100.md) or open
`colab_a100.ipynb`. That variant uses neither Docker nor ngrok and is not
security-isolated.

This example creates a small but executable agent-RL dataset with:

- 10 Python bug-fix tasks adapted from utility functions in
  `/Users/dc/cssbenchmark-aks`.
- 10 React design tasks converted from all ten CSS benchmark cases, including
  their reference screenshots and exact visual specifications.
- Hidden behavioral tests for Python and a continuous screenshot-similarity
  reward for React.
- Uni-Agent `swe_agent` rows in Parquet format, ready for GRPO training with
  veRL.

The requested path `/Users/dc/cssbenchmarks-aks` is also accepted when it
exists. On this machine the checkout is named `/Users/dc/cssbenchmark-aks`
(singular `benchmark`), which the generator detects automatically.

## Dataset layout

Generation writes:

```text
generated/
├── starter_tasks/       # copied into the sandbox image; no hidden answers
├── grading/             # hidden tests and gold solutions for verification
├── data/
│   ├── all.parquet      # all 20 samples
│   ├── train.parquet    # 8 Python + 8 React
│   ├── test.parquet     # 2 Python + 2 React
│   └── tasks.jsonl      # human-readable preview without binary archives
└── manifest.json
```

Every Parquet row includes:

- chat-formatted `prompt`
- `agent_name: swe_agent`
- a per-task sandbox setup command
- a hidden test archive and gold-solution archive
- `terminal_bench_v2` reward metadata understood by Uni-Agent

Python rewards are `0` or `1`. React rewards are continuous values in
`[0, 1]`, calculated with the original benchmark's full-frame, foreground,
edge, and layout similarities plus an overflow penalty.

## 1. Install the dataset dependency

From the Uni-Agent repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install datasets
```

For full agent training, also complete the normal Uni-Agent and veRL
installation described in the repository installation guide.

## 2. Generate the 20 tasks

```bash
python examples/mixed_code_react/generate_dataset.py \
  --css-benchmark-root /Users/dc/cssbenchmark-aks
```

For fixture-only development without `datasets`, add `--skip-parquet`.

## 3. Build the local sandbox

The common image contains Python, Node, React/Vite, Playwright Chromium,
SWE-ReX, and all starter workspaces. Hidden tests and solutions are not copied
into it.

```bash
docker build \
  -f examples/mixed_code_react/Dockerfile \
  -t uni-agent-mixed-code-react:latest \
  examples/mixed_code_react
```

## 4. Validate

Validate the manifest, all three Parquet files, and all ten Python gold
solutions:

```bash
python examples/mixed_code_react/validate_dataset.py
```

After building the image, also validate that every gold React solution earns
at least `0.99` from the visual grader:

```bash
python examples/mixed_code_react/validate_dataset.py --docker
```

For development on a host with Playwright, Chrome, and the React dependencies
already installed, the equivalent non-container check is:

```bash
python examples/mixed_code_react/validate_dataset.py \
  --host-react \
  --node-modules /path/to/react-runtime/node_modules
```

The generator itself has standard-library unit tests:

```bash
python -m unittest examples/mixed_code_react/test_generate_dataset.py
```

## 5. Run GRPO training

Start Ray, point `MODEL_PATH` at a local trainable model, and launch:

```bash
ray start --head
export MODEL_PATH="$HOME/models/Qwen3-4B-Instruct"
bash examples/mixed_code_react/train.sh
```

The defaults are intentionally small enough to serve as an example, but
agentic RL remains GPU-intensive. Adjust batch sizes, model size, response
length, rollout count, and FSDP offloading for your hardware.

## Important visual-model note

The current example supplies the design as an exact textual specification and
places `reference.png` in the workspace for provenance and grading. The
standard Uni-Agent training interface in this checkout is text/tool based; it
does not automatically send the screenshot to the policy model as a
multimodal message. To train a model that directly *sees* the screenshot,
connect a VLM-capable rollout/model adapter and add image content to the prompt.
