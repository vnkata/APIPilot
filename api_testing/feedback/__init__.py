import json
import re
from sklearn.metrics.pairwise import cosine_similarity
 
from api_testing.feedback.semantic_error_memory import SemanticErrorMemory
from api_testing.models.specification_model import ItemProperties
from api_testing.prompts.feedback_judge import FeedBackJudge
from api_testing.utils.http import isClientError, isSuccessful


def normalize_error(text):

    if not text:
        return ""
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    text = text.lower()
    text = re.sub(r'\d+', '<num>', text)
    # text = re.sub(r'\".*?\"', '<str>', text)

    return text[:500]


class FeedbackAnalyzer:

    def __init__(self, model=None, embed=None, cache_dir=None):

        self.model = model
        self.feedback_eval = FeedBackJudge(self.model)

        self.feedback = []

        # semantic memory
        self.error_memory = SemanticErrorMemory(embed, cache_dir=cache_dir)
        self.embed = embed
        self.threshold = 0.9

    # ------------------------------------------------
    # GROUP ERRORS
    # ------------------------------------------------

    def _group_errors(self, entries):

        groups = []

        for entry in entries:

            emb = entry["embedding"]

            matched = False

            for g in groups:

                score = cosine_similarity(
                    [emb],
                    [g["embedding"]]
                )[0][0]

                if score >= self.threshold:
                    g["items"].append(entry)
                    matched = True
                    break

            if not matched:

                groups.append({
                    "embedding": emb,
                    "items": [entry]
                })

        return groups

    # ------------------------------------------------
    # MAIN
    # ------------------------------------------------

    def evaluate(self, seq_path, operation, responses, producer_mapping,context_pool):
        seq_path = [
            f"{method.upper()} {endpoint}"
            for method, endpoint in (p.split("-", 1) for p in seq_path)
        ]
        def format_param_sources(data: dict) -> list[str]:
            result = []
            for name, v in data.items():
                method, path = v["source_endpoint"].split("-", 1)
                endpoint = f"{method.upper()} {path}"
                result.append(
                    f"- {name} is derived from {v['source_param']} returned by {endpoint}"
                )
            return result
        invalids = [
            entry for entry in responses
            if not entry.get("is_expected_status", True)
            and isClientError(entry.get("response", {}).get("status"))
        ]
        valids = [
            entry for entry in responses if isSuccessful(entry.get("response", {}).get("status"))
        ]
        for item in valids:
            item = item.get("request", {})
            combines = item.get("path_params") or {}
            if combines:
                context_pool.add(combines)

        entries = []
        param_sources = format_param_sources(producer_mapping)

        global_params = {
            "endpoint": f"{operation.http_method.upper()} {operation.endpoint_path}",
            "summary": ((operation.summary or "") + " " + (operation.description or "")).strip(),
            "parameters": "\n".join(
                f"- {k} : {v.to_human_readable()}"
                for k, v in operation.parameters.items()
            ),
            "parameters_sources":  "\n".join(param_sources),
            "requestBody": "\n".join(
                f"- {k} : {ItemProperties.from_dict(v).to_human_readable()}"
                for k,v in operation.get_request_body().items()
            ),
            "test_sequences": "\n".join(
                f"{i}. {p}" for i, p in enumerate(seq_path, 1)
            ),
        }
        # -----------------------------------------
        # FORMAT + CACHE LOOKUP
        # -----------------------------------------

        unresolved = []

        for entry in invalids:

            item = {
                "method": entry.get("request", {}).get("method"),
                "url": entry.get("request", {}).get("path_template"),
                "path_params": entry.get("request", {}).get("path_params"),
                "query_params": {
                    p["name"]: p["value"]
                    for p in entry.get("request", {}).get("queryString", []) or []
                },
                "request_body": entry.get("request", {}).get("postData", {}).get("text"),
                "error_response": entry.get("response", {}).get("content", {}).get("text")
            }

            norm_error = normalize_error(item.get("error_response") or "")

            norm_error = norm_error + " | " + json.dumps(
                global_params,
                sort_keys=True,
                ensure_ascii=False
            )
            # search semantic cache
            solution = self.error_memory.search(norm_error)

            if solution:
                item["feedback"] = solution

            else:

                emb = self.embed.embed(norm_error)

                item["_normalized_error"] = norm_error
                item["embedding"] = emb

                unresolved.append(item)

            entries.append(item)

        # -----------------------------------------
        # GROUP unresolved errors
        # -----------------------------------------

        if unresolved:

            groups = self._group_errors(unresolved)

            representatives = []
            for g in groups:
                item = g["items"][0].copy()
                item.pop("embedding", None)   # remove embedding field
                representatives.append(item)
            
            params = {
                **global_params,
                "operations_details": representatives
            }

            result = self.feedback_eval.exec(**params)

            solutions = result.get("datas", [])

            for group, solution in zip(groups, solutions):
                for item in group["items"]:
                    item["feedback"] = solution
                    self.error_memory.add(
                        item["_normalized_error"],
                        solution
                    )

        # cleanup
        for e in entries:
            e.pop("embedding", None)
            e.pop("_normalized_error", None)
        self.feedback = entries

    # ------------------------------------------------
    # ADJUST CONTEXT
    # ------------------------------------------------

    def adjust(self, path, context: 'ContextualMemory', producer_mapping,  operation_graph,graph_analyst, *args, **kargs):
        adjust = False
        context.set_current(path)

        for item in self.feedback:

            feedback = item.get("feedback", {})

            if feedback.get("invalid_resource_pair", False):
                combines = item.get("path_params") or {}
                if combines:
                    context.remove(combines)

            if feedback.get("invalid_parameter_source",{}):
                invalid_sources = feedback.get("invalid_parameter_source", {})
                for param, source_param in invalid_sources.items():
                    meta = producer_mapping.get(param)
                    if not meta:
                        continue

                    source_endpoint = meta.get("source_endpoint")
                    # source_param = meta.get("source_param")

                    if not source_endpoint or not source_param:
                        continue
                    operation_graph.remove_edge(
                        source_endpoint,
                        path,
                        source_param,
                        param
                    )
                    graph_analyst.remove_matching_params(
                        target_endpoint=path,
                        target_param=param,
                        source_endpoint=source_endpoint,
                        source_param=source_param
                    )
                    adjust = True

            if feedback.get("constraints", {}):
                constraints = feedback.get("constraints", {})

                # Merge constraint info into producer mapping so that generator config can be adjusted.
                for param_name, constraint_desc in constraints.items():
                    existing = producer_mapping.get(param_name, {})

                    if existing:
                        if isinstance(existing.get("constraints"), list):
                            existing["constraints"].append(constraint_desc)
                        elif existing.get("constraints"):
                            existing["constraints"] = [existing.get("constraints"), constraint_desc]
                        else:
                            existing["constraints"] = [constraint_desc]
                    else:
                        existing = {"constraints": [constraint_desc]}

                    producer_mapping[param_name] = existing

                    # Update graph operation parameter description if possible.
                    if operation_graph is not None and path in operation_graph.nodes:
                        node = operation_graph.nodes.get(path)
                        if node and hasattr(node, "parameters"):
                            param_obj = node.parameters.get(param_name)
                            if param_obj is not None:
                                old_desc = param_obj.description or ""
                                param_obj.description = (
                                    f"{old_desc} [constraint: {constraint_desc}]".strip()
                                )

                        if node and hasattr(node, "request_body"):
                            request_field = node.request_body.get(param_name)
                            if request_field is not None and hasattr(request_field, "description"):
                                old_desc = request_field.description or ""
                                request_field.description = (
                                    f"{old_desc} [constraint: {constraint_desc}]".strip()
                                )

                adjust = True

        # context.clear_current()
        return adjust