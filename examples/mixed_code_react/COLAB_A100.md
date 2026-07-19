# Colab A100: native veRL with no coding sandbox

This variant runs all three parts in one hosted Colab VM:

- veRL/FSDP training on the A100
- vLLM rollouts on the same A100
- agent shell commands and reward tests directly on the Colab host

Docker and ngrok are not used.

> **Danger:** this configuration intentionally has no security boundary.
> Model-generated commands can inspect or destroy the entire Colab runtime,
> including model files, checkpoints, tokens, and mounted Drive contents.
> Use a disposable runtime, a public model that needs no token, and do not
> mount Google Drive until training has stopped.
>
> The agent can also inspect the repository and training Parquet files, which
> contain verifier archives and gold-solution assets. Consequently this mode
> is suitable for pipeline experimentation, but its rewards are not a secure
> benchmark and may be vulnerable to reward hacking.

## 1. Put the repository in Colab

Upload or clone this checkout to `/content/uniagent`, then select an A100:

```text
Runtime → Change runtime type → A100 GPU
```

Verify it:

```bash
!nvidia-smi -L
```

## 2. Install directly in the Colab Python environment

```bash
%cd /content/uniagent
!bash examples/mixed_code_react/setup_colab_a100.sh
```

Restart the Colab runtime after this cell. The setup may replace Colab's
preinstalled PyTorch stack with the versions required by vLLM.

## 3. Prepare host-execution Parquet rows

After reconnecting:

```bash
%cd /content/uniagent
!python examples/mixed_code_react/prepare_colab_host_data.py \
  --repo-root /content/uniagent \
  --node-modules /content/uniagent-react-runtime/node_modules
```

This produces `train_colab_host.parquet`, `test_colab_host.parquet`, and
`all_colab_host.parquet`. Their setup commands reset `/workspace` before every
episode and copy in the appropriate starter task.

## 4. Run the native A100 experiment

```bash
%cd /content/uniagent
!MODEL_PATH=Qwen/Qwen3-0.6B \
  bash examples/mixed_code_react/train_colab_a100.sh
```

The conservative defaults are one agent worker, one in-flight coding
trajectory, two GRPO rollouts per prompt, batch size two, and a 2,048-token
response budget. Checkpoints are written to `/content/uniagent-checkpoints`.

Copy checkpoints to Drive only after training has stopped. Mounting Drive
during agent rollouts gives model-generated shell commands access to it.

## Why there is no ngrok

Ngrok is useful when the coding environment is a separate machine. In this
variant the model and coding environment are the same Colab VM, so all
communication is local. An ngrok tunnel would add exposure and latency without
providing isolation.
