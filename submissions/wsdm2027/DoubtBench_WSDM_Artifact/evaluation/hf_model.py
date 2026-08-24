"""Load open Hugging Face causal language models for DoubtBench."""

from __future__ import annotations

import os


def load_hf_model(model_name: str, cache_dir: str | None):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    # Prefer Transformers' native Phi-3 implementation over remote repo code.
    default_trust_remote_code = not model_name.lower().startswith("microsoft/phi-3")
    override = os.getenv("HF_TRUST_REMOTE_CODE")
    trust_remote_code = (
        default_trust_remote_code
        if override is None
        else override.strip().lower() in {"1", "true", "yes", "on"}
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir,
        trust_remote_code=trust_remote_code,
    )
    if tokenizer.pad_token_id is None and tokenizer.eos_token_id is not None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    kwargs = {
        "cache_dir": cache_dir,
        "trust_remote_code": trust_remote_code,
        "device_map": "auto",
    }
    if torch.cuda.is_available():
        kwargs["torch_dtype"] = torch.bfloat16
    model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
    model.eval()
    return tokenizer, model
