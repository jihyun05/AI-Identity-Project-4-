from __future__ import annotations

from .self_negation import SelfNegationEvaluator

# 새 evaluator를 추가하려면 클래스를 만들고 여기에 등록만 하면 됨.
_REGISTRY = {
    "self_negation": SelfNegationEvaluator,
}


def build_evaluators(names: list[str], **kwargs) -> list:
    return [_REGISTRY[name](**kwargs.get(name, {})) for name in names]
