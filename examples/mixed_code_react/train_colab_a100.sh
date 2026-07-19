#!/usr/bin/env bash
# Native single-A100 GRPO run. Coding tools execute directly in the same VM.
set -xeuo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${repo_root}"

export PYTHONPATH="${repo_root}:${repo_root}/verl${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=true
export VLLM_USE_V1=1
export VLLM_DISABLE_COMPILE_CACHE=1
export TORCH_NCCL_AVOID_RECORD_STREAMS=1
export CUDA_DEVICE_MAX_CONNECTIONS=1

project_name=${PROJECT_NAME:-Uni-Agent-Mixed-Code-React-Colab}
exp_name=${EXP_NAME:-GRPO-Qwen3-0.6B-A100-Host}

MODEL_PATH=${MODEL_PATH:-Qwen/Qwen3-0.6B}
TRAIN_FILE=${TRAIN_FILE:-examples/mixed_code_react/generated/data/train_colab_host.parquet}
TEST_FILE=${TEST_FILE:-examples/mixed_code_react/generated/data/test_colab_host.parquet}
AGENT_CONFIG_PATH=${AGENT_CONFIG_PATH:-examples/mixed_code_react/agent_config_colab_host.yaml}
CKPTS_DIR=${CKPTS_DIR:-/content/uniagent-checkpoints}

test -f "${TRAIN_FILE}"
test -f "${TEST_FILE}"
nvidia-smi

python3 -m verl.trainer.main_ppo \
  --config-name='ppo_trainer.yaml' \
  hydra.searchpath=[pkg://verl.trainer.config] \
  data.train_files="${TRAIN_FILE}" \
  data.val_files="${TEST_FILE}" \
  data.prompt_key=prompt \
  data.max_prompt_length=4096 \
  data.max_response_length=2048 \
  data.filter_overlong_prompts=True \
  data.truncation=error \
  data.return_raw_chat=True \
  data.train_batch_size=2 \
  actor_rollout_ref.model.path="${MODEL_PATH}" \
  actor_rollout_ref.model.use_fused_kernels=False \
  actor_rollout_ref.actor.use_dynamic_bsz=True \
  actor_rollout_ref.actor.ppo_mini_batch_size=2 \
  actor_rollout_ref.actor.ppo_max_token_len_per_gpu=8192 \
  actor_rollout_ref.actor.optim.lr=1e-6 \
  actor_rollout_ref.actor.fsdp_config.param_offload=True \
  actor_rollout_ref.actor.fsdp_config.optimizer_offload=True \
  actor_rollout_ref.actor.entropy_coeff=0 \
  actor_rollout_ref.rollout.n=2 \
  actor_rollout_ref.rollout.name=vllm \
  actor_rollout_ref.rollout.mode=async \
  actor_rollout_ref.rollout.tensor_model_parallel_size=1 \
  actor_rollout_ref.rollout.gpu_memory_utilization=0.4 \
  actor_rollout_ref.rollout.enforce_eager=True \
  actor_rollout_ref.rollout.multi_turn.enable=True \
  actor_rollout_ref.rollout.multi_turn.max_assistant_turns=8 \
  actor_rollout_ref.rollout.multi_turn.max_parallel_calls=1 \
  actor_rollout_ref.rollout.agent.num_workers=1 \
  actor_rollout_ref.rollout.agent.agent_loop_config_path="${AGENT_CONFIG_PATH}" \
  actor_rollout_ref.rollout.agent.default_agent_loop=swe_agent \
  actor_rollout_ref.rollout.calculate_log_probs=True \
  actor_rollout_ref.rollout.free_cache_engine=True \
  actor_rollout_ref.hybrid_engine=True \
  actor_rollout_ref.ref.fsdp_config.param_offload=True \
  algorithm.adv_estimator=grpo \
  algorithm.use_kl_in_reward=False \
  algorithm.kl_ctrl.kl_coef=0.0 \
  reward.reward_manager.name=dapo \
  trainer.logger=['console'] \
  trainer.project_name="${project_name}" \
  trainer.experiment_name="${exp_name}" \
  trainer.val_before_train=False \
  trainer.save_freq=1 \
  trainer.test_freq=1 \
  trainer.total_epochs=3 \
  trainer.default_local_dir="${CKPTS_DIR}" \
  trainer.nnodes=1 \
  trainer.n_gpus_per_node=1
