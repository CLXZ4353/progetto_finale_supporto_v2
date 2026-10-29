# -*- coding: utf-8 -*-
"""Test delle funzioni pure di selezione e profilo dei modelli."""
from __future__ import annotations

from supporto.config import Settings
from supporto.models import (
    dedupe_models,
    final_reasoning_effort,
    is_lfm3,
    is_model_visible,
)


def test_is_lfm3_e_visibilita():
    assert is_lfm3("lfm3-1.7b@q4_k_m")
    assert is_lfm3("LFM3-1.7b")
    assert not is_lfm3("llama-3.2-3b-instruct")
    assert not is_model_visible("lfm3-1.7b@bf16")
    assert not is_model_visible("meta-llama/llama-3.2-3b-instruct")
    assert is_model_visible("llama-3.2-3b-instruct")


def test_dedupe_models_unisce_alias_e_tiene_il_preferito():
    options = dedupe_models(
        ["lfm3-1.7b@q4_k_m", "lfm3-1.7b", "llama-3.2-3b-instruct"],
        preferred="lfm3-1.7b@q4_k_m",
    )
    assert options == ["lfm3-1.7b@q4_k_m", "llama-3.2-3b-instruct"]


def test_dedupe_models_inserisce_il_preferito_assente():
    options = dedupe_models(
        ["llama-3.2-3b-instruct"], preferred="lfm3-1.7b@q4_k_m"
    )
    assert options == ["lfm3-1.7b@q4_k_m", "llama-3.2-3b-instruct"]


def test_dedupe_models_non_aggiunge_modelli_nascosti():
    options = dedupe_models(
        ["meta-llama/llama-3.2-3b-instruct", "llama-3.2-3b-instruct"],
        preferred="lfm3-1.7b@bf16",
    )
    assert options == ["llama-3.2-3b-instruct"]


def test_final_reasoning_effort_solo_per_lfm3_locale():
    assert (
        final_reasoning_effort(
            Settings(model_backend="local", lm_studio_model="lfm3-1.7b@q4_k_m")
        )
        == "none"
    )
    assert (
        final_reasoning_effort(
            Settings(
                model_backend="local", lm_studio_model="llama-3.2-3b-instruct"
            )
        )
        is None
    )
    assert (
        final_reasoning_effort(
            Settings(model_backend="gemini", lm_studio_model="lfm3-1.7b@q4_k_m")
        )
        is None
    )
