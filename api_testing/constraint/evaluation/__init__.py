from pathlib import Path
from typing import Any, Dict, List, Tuple

from lark import Lark
from .engine.evaluator import DSLTransformer


class DSLEvaluationContext:
    def __init__(self, root: dict, local: dict | None = None):
        self.root = root or {}
        self.local = local or {}

    def get(self, name: str, default: Any = None) -> Any:
        if name == "self":
            return self.local.get("self", self.root.get("self", default))

        if name in self.local:
            return self.local[name]

        if name in self.root:
            return self.root[name]

        if "." in name or "[]" in name:
            resolved_local = self._resolve_path(name, self.local)
            if resolved_local is not None:
                return resolved_local

            resolved_root = self._resolve_path(name, self.root)
            if resolved_root is not None:
                return resolved_root

        return default
    @staticmethod
    def _is_missing(value):

        if value is None:
            return True

        if isinstance(value, list):

            if not value:
                return True

            return all(
                DSLEngine._is_missing(v)
                for v in value
            )

        return False

    def _resolve_path(self, path: str, container: Any) -> Any:
        if container is None:
            return None

        values: List[Any] = [container]
        for token in path.split("."):
            next_values: List[Any] = []
            wildcard = token.endswith("[]")
            key = token[:-2] if wildcard else token

            for value in values:
                if isinstance(value, dict) and key in value:
                    next_value = value[key]
                    if wildcard:
                        if isinstance(next_value, list):
                            next_values.extend(next_value)
                    else:
                        next_values.append(next_value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and key in item:
                            next_value = item[key]
                            if wildcard:
                                if isinstance(next_value, list):
                                    next_values.extend(next_value)
                            else:
                                next_values.append(next_value)

            values = next_values
            if not values:
                return None

        if len(values) == 1:
            return values[0]
        return values


class DSLEngine:
    def __init__(self, grammar_path: str | None = None, parser: str = "lalr"):
        grammar_file = Path(grammar_path) if grammar_path else Path(__file__).resolve().parent / "grammar.lark"
        if grammar_file.is_dir():
            grammar_file = grammar_file / "grammar.lark"

        with open(grammar_file, "r", encoding="utf-8") as f:
            grammar = f.read()

        self._parser = Lark(grammar, parser=parser)

    def evaluate(self, dsl: str, context: dict):
        """
        Parse + evaluate DSL với context runtime
        """
        eval_context = DSLEvaluationContext(context)
        tree = self._parser.parse(dsl)
        transformer = DSLTransformer(eval_context)
        return transformer.transform(tree)

    def validate(self, rules: dict, context: dict) -> Dict[str, bool]:
        results: Dict[str, bool] = {}

        for path, dsl in rules.items():
            try:
                results[path] = self._validate_path(path, dsl, context)
            except Exception as e:
                print(f"Error validating rule for path '{path}': {e}")
                results[path] = False
        return results
    
    def _common_parent(self, paths: list[str]) -> str:
        split_paths = [p.split(".") for p in paths]

        result = []

        for parts in zip(*split_paths):
            if len(set(parts)) == 1:
                result.append(parts[0])
            else:
                break

        return ".".join(result)
    def _validate_multi_path(
        self,
        path: str,
        dsl: str,
        context: dict
    ):
        paths = [p.strip() for p in path.split(",")]
        parent = self._common_parent(paths)
        targets = self._collect_targets(parent, context)
        results = []
        for local_obj, _ in targets:
            local_context = self._build_local_context(
                local_obj,
                local_obj
            )
            eval_context = DSLEvaluationContext(
                context,
                local_context
            )
            tree = self._parser.parse(dsl)
            transformer = DSLTransformer(eval_context)
            value = transformer.transform(tree)
            results.append(bool(value))
        return all(results)

    def _validate_path(self, path: str, dsl: str, context: dict) -> bool:
        if "," in path:
            return self._validate_multi_path(path, dsl, context)
        targets = self._collect_targets(path, context)

        if not targets:
            print(f"Warning: No targets found for path '{path}'. DSL: {dsl}")
            return True

        results: List[bool] = []
        for local_obj, self_value in targets:
            local_context = self._build_local_context(local_obj, self_value)
            local_context[path] = self_value  # ensure the target path is available in local context
            eval_context = DSLEvaluationContext(context, local_context)
            tree = self._parser.parse(dsl)
            transformer = DSLTransformer(eval_context)
            if self._is_missing(self_value):
                print(f"Warning: Target value for path '{path}' is None. DSL: {dsl}")
                value = True
            else:
                value = transformer.transform(tree)
            if value == False: 
                print(f"Validation failed for path '{path}' with value '{self_value}'. DSL: {dsl}")
            results.append(bool(value))
        return all(results)

    def _build_local_context(self, local_obj: Any, self_value: Any) -> dict:
        local_context: dict = {"self": self_value}
        if isinstance(local_obj, dict):
            local_context.update(local_obj)
        return local_context

    def _collect_targets(self, path: str, context: dict) -> List[Tuple[Any, Any]]:
        tokens = path.split(".")
        is_list_target = tokens[-1].endswith("[]")
        path_to_parent = tokens if is_list_target else tokens[:-1]

        current: List[Any] = [context]
        for token in path_to_parent:
            current = self._resolve_step(current, token)
            if not current:
                return []

        if is_list_target:
            return [(item, item) for item in current]

        leaf = tokens[-1]
        if leaf.endswith("[]"):
            return [(item, item) for item in self._resolve_step(current, leaf)]

        results: List[Tuple[Any, Any]] = []
        for item in current:
            if isinstance(item, dict) and leaf in item:
                results.append((item, item[leaf]))

        return results

    def _resolve_step(self, sources: List[Any], token: str) -> List[Any]:
        wildcard = token.endswith("[]")
        key = token[:-2] if wildcard else token

        next_values: List[Any] = []
        for value in sources:
            if isinstance(value, dict) and key in value:
                next_value = value[key]
                if wildcard:
                    if isinstance(next_value, list):
                        next_values.extend(next_value)
                else:
                    next_values.append(next_value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and key in item:
                        next_value = item[key]
                        if wildcard:
                            if isinstance(next_value, list):
                                next_values.extend(next_value)
                        else:
                            next_values.append(next_value)

        return next_values