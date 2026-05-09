from collections import defaultdict, deque
import concurrent.futures
import copy
import json
import logging
import random
from time import sleep
import time
import asyncio
from dotenv import load_dotenv
from api_testing.configuration.configuration_parser import ConfigurationParser
# from api_testing.constraint.static_constraint_miner import StaticConstraintMiner
from api_testing.feedback import FeedbackAnalyzer
from api_testing.generators.executor import Executor, Strategy
from api_testing.generators.requestor import Requestor
from api_testing.generators.smart_value_generator import SmartValueGenerator
from api_testing.graph.graph_analyzer import GraphAnalyzer
from api_testing.memory.contextual_memory import ContextualMemory
from api_testing.models.configuration_model import FieldConfiguration
from api_testing.prompts.request_response_constraint import RequestResponseConstraint
# from api_testing.tracing.tracing import TraceManager
from api_testing.utils import flatten_json_schema, to_dict_helper
from api_testing.utils.common import remove_nulls
from api_testing.utils.http import isSuccessful
from collections import defaultdict

from api_testing.utils.llm_tracker import initTracker

from .memory import (
    APITestingVectorDB
)

from .models import (
    APITestingBaseLLMModel,
    APITestingBaseEmbeddingModel,
    GeminiModel,
    OllamaModel,
    HuggingfaceEmbeddingModel,
    OllamaEmbeddingModel
)

from .graph import (
    OperationGraph,
    OperationNode,
    OperationEdge
)
from typing import Dict, Optional, Set, Union, List
from api_testing.dataset import SpecificationParser
from api_testing.graph import OperationGraph
from api_testing.models import APITestingBaseEmbeddingModel, APITestingBaseLLMModel
from api_testing.config.config_loader import (
    apply_cli_overrides,
    build_embedder,
    build_llm,
    load_config,
)
from api_testing.config.config_wizard import run_wizard
import shutil
import os
from api_testing.events import get_emitter, EventType, Phase, OperationStatus
from api_testing.tui.app import TUIApp
from api_testing.utils.log import (
    configure_logging,
    getLogger,
    restore_console_logging,
    set_console_level,
    suppress_console_logging,
)
from typing import List, Dict, Set, Any
import argparse


DEFAULT_SETUP_MAX_WORKERS = max(1, int(os.getenv("API_TESTING_SETUP_MAX_WORKERS", "2")))
DEFAULT_ASYNC_MAX_CONCURRENT = int(os.getenv("API_TESTING_ASYNC_MAX_CONCURRENT", "50"))
DEFAULT_MAX_REQUEST_WORKERS = int(os.getenv("API_TESTING_MAX_REQUEST_WORKERS", "10"))

def parse_args():
    parser = argparse.ArgumentParser(
        description="APITesting - Automated REST API Testing with LLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  apitesting                    # Run TUI wizard and write configurations.toml
  apitesting --init-config     # Create configurations.toml and exit
  apitesting --skip-wizard     # Use configurations.toml directly

Tip: set run.debug = true in configurations.toml to disable TUI.

For more information, visit: https://github.com/thanhtuit96/API-Testing
        """,
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configurations.toml (default: configurations.toml)",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Run TUI wizard to create configurations.toml and exit",
    )
    parser.add_argument(
        "--skip-wizard",
        action="store_true",
        help="Skip wizard and run tests using configurations.toml",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick setup wizard (essential settings only)",
    )
    parser.add_argument(
        "-s",
        "--spec",
        type=str,
        default=None,
        help="Override specification path (relative to project root)",
    )
    parser.add_argument(
        "--async",
        dest="async_mode",
        action="store_true",
        default=None,
        help="Enable async HTTP requests for faster execution (uses httpx.AsyncClient)",
    )
    parser.add_argument(
        "--async-max-concurrent",
        type=int,
        default=None,
        help=f"Maximum concurrent async requests (default: {DEFAULT_ASYNC_MAX_CONCURRENT})",
    )
    parser.add_argument(
        "-g",
        "--generations",
        type=int,
        default=None,
        help="Number of test generations to run",
    )
    parser.add_argument(
        "-c",
        "--test-cases",
        type=int,
        default=None,
        help="Number of test cases per endpoint",
    )
    parser.add_argument(
        "--mutation-ratio",
        type=float,
        default=None,
        help="Ratio of mutated requests to induce 4xx errors",
    )
    parser.add_argument(
        "--header-mutation-ratio",
        type=float,
        default=None,
        help="Ratio of header mutations",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum concurrent request workers (default: auto)",
    )
    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()

    config_path = args.config or "configurations.toml"
    if args.init_config:
        run_wizard(config_path, quick_mode=args.quick)
        return

    config = load_config(config_path)
    config = apply_cli_overrides(config, args)

    if not config["project"]["spec_path"]:
        print("[yellow]No spec_path configured. Running wizard...[/yellow]")
        print()
        run_wizard(config_path, quick_mode=args.quick)
        config = load_config(config_path)
        config = apply_cli_overrides(config, args)

    llm = build_llm(config)
    embedder = build_embedder(config)
    headers = config.get("headers", {})
    run = config["run"]
    debug_mode = bool(run.get("debug", False))

    tester = APITesting(
        base_url=config["project"]["base_url"],
        base_title=config["project"].get("base_title") or None,
        spec_path=config["project"]["spec_path"],
        model=llm,
        embedder=embedder,
    )

    tui_app = None
    if debug_mode:
        set_console_level(logging.DEBUG)
    else:
        set_console_level(logging.INFO)
        tui_app = TUIApp()
        tui_app.start()
        suppress_console_logging()

    start_time = time.perf_counter()
    total_testcase = 0
    successFull = {}
    try:
        total_testcase, successFull = tester.run_tests(
            num_generations=run["num_generations"],
            num_test_cases=run["num_test_cases"],
            mutation_ratio=run["mutation_ratio"],
            header_mutation_ratio=run["header_mutation_ratio"],
            async_mode=run["async_mode"],
            max_request_workers=run["max_request_workers"],
            async_max_concurrent=run["async_max_concurrent"],
            headers=headers,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    finally:
        elapsed = time.perf_counter() - start_time
        if not debug_mode and tui_app is not None:
            restore_console_logging()
            tui_app.stop()
            tui_app.print_final_report(
                title=tester.base_title,
                duration_seconds=elapsed,
                total_requests=total_testcase,
                status_distribution={},
                total_operations=len(successFull),
                successful_operations=len(successFull),
                unique_5xx_errors=0,
            )

def sort_children_by_method(children_values):
    # Định nghĩa trọng số ưu tiên
    method_priority = {
        "post": 1,
        "get": 2,
        "put": 3,
        "delete": 4
    }

    def get_priority(child):
        name = getattr(child, 'name', '').lower()
        # Tách lấy phần method trước dấu "-"
        # Ví dụ: "post-/projects" -> "post"
        method_part = name.split('-')[0] if '-' in name else name
        
        # Trả về trọng số, nếu không khớp thì cho xuống cuối (99)
        return method_priority.get(method_part, 99)

    return sorted(children_values, key=get_priority)

class APITesting:
    def __init__(self,
                 base_url: Optional[str] = None,
                 base_title: Optional[str] = None,
                 spec_path: str = None,
                 model: Optional[Union[str, APITestingBaseLLMModel]] = None,
                 critic_model: Optional[Union[str,
                                              APITestingBaseLLMModel]] = None,
                 embedder: Optional[Union[str,
                                          APITestingBaseEmbeddingModel]] = None,
                 vector_db: Optional[Union[str,
                                           APITestingVectorDB]] = None,
                 test_single_endpoint: Optional[str] = None,  # New parameter
                 # async_mode=False,

                 ):
        self.base_url = base_url
        self.base_title = base_title
        self.spec_path = spec_path
        self.embedder = embedder
        self.model = model
        self.critic_model = critic_model or model # judge model
        self.vector_db = vector_db
        self.project_dir = None
        self.test_single_endpoint = test_single_endpoint
        self.operation_graph = None
        self.tracer = None
        self.logger = logging.getLogger(__name__)
        self._load_()
        
        if self.test_single_endpoint:
            self.init_graph_for_single_endpoint(self.test_single_endpoint)
        else:
            self.init_graph()

    def _load_(self):
        #  get tile from spec_path
        self.spec_parser = SpecificationParser(spec_path=self.spec_path)
        if self.base_title is None:
            self.base_title = self.spec_parser.get_api_title()
        if self.base_url is None:
            self.base_url = self.spec_parser.get_api_url()
        # mkir project if not exist
        self.project_dir = os.path.join(os.getcwd(), ".cache", self.base_title)
        cache_dir_created = False
        if not os.path.exists(self.project_dir):
            cache_dir_created = True
            os.makedirs(self.project_dir)
            # change pwd to project_dir
            _, file_extension = os.path.splitext(self.spec_path)
            shutil.copyfile(
                self.spec_path, os.path.join(self.project_dir, f"baseline_specification{file_extension}"))
        # logger
        # self.tracer = TraceManager(
        #     trace_path=self.project_dir,
        #     llm_model=self.model.get_model_name(),
        #     level=logging.DEBUG
        # )
        configure_logging(
            class_name=__name__,
            log_dir=self.project_dir,
            llm_model=self.model.get_model_name(),
            level=logging.DEBUG,
        )
        set_console_level(logging.DEBUG)
        self.logger = getLogger(__name__)
        if cache_dir_created:
            self.logger.debug("Created cache directory at %s", self.project_dir)
        initTracker(dir=self.project_dir, model=self.model.get_model_name())
        self.spec_parser.load_or_initialize(cache_dir=self.project_dir)
        # self._preprocess_()
    
    def build_odg(self):
        self.operation_graph = OperationGraph(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        self.operation_graph.create_graph()
        self.operation_graph.save_graph_to_cache()

    def build_config(self):
        parser = ConfigurationParser(spec_parser=self.spec_parser, model=self.model,cache_dir=self.project_dir)
        parser.parse()

    # def process(self):
        
    #     self.build_odg()
    #     self.build_config()
    #     with open(os.path.join(self.project_dir,"semantic_property_dependency_graph.json"), "r", encoding="utf-8") as f:
    #         graph_data = json.load(f)
    #     endpoint_groups = build_endpoint_groups(graph_data)
    #     with open(os.path.join(self.project_dir,"producer_pool.json"), "w", encoding="utf-8") as f:
    #         f.write(json.dumps(endpoint_groups, indent=4, ensure_ascii=False))

    #     for endpoint in self.parser.configurations:
    #         for param in endpoint.params.keys():
    #             for k,v in endpoint_groups.items():
    #                 if f'{endpoint.method}-{endpoint.endpoint}_params_{param}' in v:
    #                     endpoint.params[param] = FieldConfiguration(name=param, type="ProducerGenerator",genParameters={"pool": k} )
    #     self.parser.json_output()

        # process
    
    def _preprocess_(self):
        # extract contrains
        constraints = {}
        for operation, details in self.spec_parser.operations.items():
            self.logger.debug("Extract constraints for %s", operation)
            simple = details.simple_operation()
            # parameters
            parameters = '\n'.join([
                f'{k}:{v}' for k, v in simple["parameters"].items()
            ])
            response = simple["responses"]
            # Querys =
            query = details.http_method.upper() + " " + details.endpoint_path + \
                " : " + details.description

            results = self.vector_db.search(query=query)
            # query to string
            extras = "\n=========\n".join([res.content for res in results])
            #  read RAGS
            miner = RequestResponseConstraint(
                llm=self.model, endpoint=f"{details.http_method} {details.endpoint_path}", parameters=parameters, response=response, extras=extras)
            constraint = miner.validate()
            constraints[operation] = to_dict_helper(constraint)["constraint"]
            # Contraints
        file_name = os.path.join(
            self.project_dir, f"request_resonponse_constraint.json")
        with open(file_name, 'w', encoding='utf-8') as file:
            json.dump(constraints, file, ensure_ascii=False, indent=4)

    def init_graph(self):
        # miner = StaticConstraintMiner(spec_parser=self.spec_parser,
        #     model=self.model,
        #     embedding_model=self.embedder,cache_dir=self.project_dir)
        # miner.response_properties_constraints()

        self.operation_graph = OperationGraph(
            spec_parser=self.spec_parser,
            model=self.model,
            embedding_model=self.embedder,
            cache_dir=self.project_dir
        )
        self.operation_graph.plot_graph()
    
    def run_tests(self, num_generations=1, num_test_cases=20, mutation_ratio=0.0, header_mutation_ratio=0.5,
                  async_mode: bool = False, max_request_workers: Optional[int] = None,
                  async_max_concurrent: int = DEFAULT_ASYNC_MAX_CONCURRENT,
                  headers: Optional[Dict[str, str]] = None):
        def build_graph_for_run():
            return OperationGraph(
                spec_parser=self.spec_parser,
                model=self.model,
                embedding_model=self.embedder,
                cache_dir=self.project_dir,
            )

        def load_config_for_run():
            return ConfigurationParser(
                spec_parser=self.spec_parser,
                model=self.model,
                cache_dir=self.project_dir,
            )

        self.logger.debug("Building operation graph and configuration")
        emitter = get_emitter()
        emitter.emit(EventType.PHASE_START, Phase.GRAPH_BUILD, message="Building operation graph...")
        if async_mode:
            with concurrent.futures.ThreadPoolExecutor(max_workers=DEFAULT_SETUP_MAX_WORKERS) as setup_pool:
                graph_future = setup_pool.submit(build_graph_for_run)
                config_future = setup_pool.submit(load_config_for_run)
                self.operation_graph = graph_future.result()
                parser = config_future.result()
        else:
            self.operation_graph = build_graph_for_run()
            parser = load_config_for_run()

        configurations = { f"{conf.method}-{conf.endpoint}": conf for conf in parser.configurations}
        nodes = self.operation_graph.nodes
        emitter.emit(EventType.PHASE_COMPLETE, Phase.GRAPH_BUILD,
                    message=f"Graph built with {len(nodes)} operations")
        context = ContextualMemory(cache_dir=self.project_dir)

        total_testcase = 0
        total_success = 0
        successFull = {}
        # process producer
        # edges = []
        adjacency_map  = {}
        properties = defaultdict(list)

        for edge in self.operation_graph.edges:
            adjacency_map.setdefault(edge.from_node.uuid, []).append(edge)
            properties[edge.from_node.uuid].append(edge)
        producer_map = {}

        def extract_xrefs_for_keys(keys, flatten):
            """
            Trích ra xrefs tương ứng cho danh sách key từ flatten schema.
            Trả về dict { key: xrefs_value hoặc None }
            """
            return {
                key: flatten.get(key, {}).get("xrefs")
                for key in keys
            }
        for uuid, edge in adjacency_map.items():
            producer_map[uuid] = {sp.value1 for e in edge for sp in e.similar_parameters}
            flatten = flatten_json_schema(nodes.get(uuid).successful_responses.to_dict())
            producer_map[uuid] = remove_nulls(extract_xrefs_for_keys(producer_map[uuid], flatten))
            properties[uuid] =  extract_xrefs_for_keys(producer_map[uuid], flatten)   
            
        parser.update_conf(self.operation_graph, producer_map)

        emitter.emit(EventType.PHASE_START, Phase.CONFIG_BUILD, message="Building configuration...")
        emitter.emit(EventType.PHASE_COMPLETE, Phase.CONFIG_BUILD,
                    message=f"Configuration built for {len(configurations)} operations")

        # pick
        graph_analyst = GraphAnalyzer(graph=self.operation_graph, cache_dir=self.project_dir)
        feedback_analyzer = FeedbackAnalyzer(model=self.model, embed=self.embedder, cache_dir=self.project_dir)

        emitter.emit(EventType.PHASE_START, Phase.GRAPH_ANALYZE, message="Analyzing dependency graph...")

        forest = graph_analyst.export_to_forest()

        emitter.emit(EventType.PHASE_COMPLETE, Phase.GRAPH_ANALYZE,
                    message=f"Found {len(forest)} root operations")
      
        def traverse_dfs(node, depth=0, context_pool: ContextualMemory = None, parent=None, seq_path = []):
            nonlocal total_testcase, total_success, forest
            context_pool = context_pool or ContextualMemory()
            # 
            self.logger.debug("%s• %s", "  " * depth, node.name)

            configuration = copy.copy(configurations.get(node.name))
            # test
            producer = { param: conf for param, conf in configuration.params.items() if conf.type == "ProducerGenerator"}
            producer_mapping = {}
            context_pool.set_current(node.name)
            # collect prefix -> keys
            prefix_groups = defaultdict(set)
            for k, params in node.matched_params.items():
                for p in params:
                    sp = p.get("source_param")
                    if sp:
                        prefix_groups[sp.rsplit(".", 1)[0]].add(k)

            # best prefix shared by most params
            best_prefix = max(prefix_groups, key=lambda x: len(prefix_groups[x]), default=None)
            common_res = None
            for k, producer_obj in producer.items():
                candidates = node.matched_params.get(k)
                if not candidates:
                    continue
                prioritized = [p for p in candidates if best_prefix and p.get("source_param","").startswith(best_prefix)]
                param = random.choice(prioritized or candidates)
                se = param.get("source_endpoint")
                sp = param.get("source_param")
                resource = producer_map.get(se, {}).get(sp)
                resource = resource.split(",")[0] if resource else None
                # 
                if parent is not None:
                    if resource and resource not in self.operation_graph.nodes[parent.name].schemas.keys():
                        key = sp.split(".")[-1]
                        if key in self.operation_graph.nodes[parent.name].required_parameters:
                            key = key + ":path"
                        data = {"resource": resource, "key": key, "need_change": True, **param}
                    else:
                        common_res = resource
                        data = {"resource": resource, "key": sp.split(".")[-1], **param}
                else:
                    data = {"resource": resource, "key": sp.split(".")[-1], **param}
                    # producer_obj.genParameters = {"pool": [data]}
                producer_mapping[k] = data
            for k, producer_obj in producer.items():
                if k in producer_mapping:
                    data = producer_mapping[k]
                    if data.get("need_change"):
                        if common_res is not None:
                            data["resource"] = common_res
                        del data["need_change"]
                        producer_mapping[k] = data
                    producer_obj.genParameters = {"pool": [data]}

            emitter.emit(
                EventType.OPERATION_UPDATE,
                phase=Phase.TEST_EXECUTION,
                operation_name=node.name,
                operation_method=node.name.split('-')[0] if '-' in node.name else '',
                operation_path=node.name,
                status=OperationStatus.RUNNING,
                generation=idx + 1,
                total_generations=num_generations,
            )

            executor = Executor(
                api_url = self.base_url,
                strategy= Strategy.NAIVE_VALUE,
                operation=nodes.get(node.name),
                cache_dir=self.project_dir,
                model=self.model,
                num_test_cases=num_test_cases,
                configuration=configurations.get(node.name),
                mutation_ratio=mutation_ratio,
                header_mutation_ratio=header_mutation_ratio,
                context_pool=context_pool,
                max_request_workers=max_request_workers,
                use_async=async_mode,
                async_max_concurrent=async_max_concurrent,
                default_headers=headers,
            )

            if async_mode:
                import asyncio
                responses = asyncio.run(executor.exec_async())
            else:
                responses = executor.exec()
            feedback = feedback_analyzer.evaluate(seq_path, operation=nodes.get(node.name),  responses=responses, producer_mapping=producer_mapping,context_pool=context_pool)
            adjug = feedback_analyzer.adjust(node.name, context_pool, producer_mapping,  self.operation_graph, graph_analyst= graph_analyst)
            if adjug:
                forest = graph_analyst.export_to_forest()
            # successfull responses  
            success_responses = [ 
                entry
                for entry in responses if isSuccessful(entry.get("response",{}).get("status",0)) 
            ]
            context_pool.update_with_responses(success_responses, properties.get(node.name))
            self.logger.debug(
                "Success %s with context_pool %s",
                len(success_responses),
                context_pool,
            )
            total_success +=  len(success_responses)
            total_testcase +=  len(responses)
            context_pool.clear_current()
            if len(success_responses)   > 0:
                successFull.update({node.name: 1})
                for child in sort_children_by_method(node.children.values()):
                    traverse_dfs(child, depth + 1, context_pool, node, seq_path=seq_path + [child.name])
            
            # save pool
           

        def traverse_forest_dfs(forest,context):
            """Duyệt toàn bộ rừng"""
            for root_node in sort_children_by_method(forest.values()):
                self.logger.debug("Root: %s", root_node.name)
                traverse_dfs(root_node, depth=1, context_pool=context , seq_path=[root_node.name])

        def _find_node_in_forest(forest, node_name):
            """Find TreeNode by name across all trees in the forest."""
            def search(node):
                if node.name == node_name:
                    return node
                for child in node.children.values():
                    result = search(child)
                    if result:
                        return result
                return None
            for root in forest.values():
                result = search(root)
                if result:
                    return result
            return None

        async def _execute_node_async(node, depth, context_pool, parent, seq_path, forest_lock=None):
            """Execute a single node and return responses."""
            nonlocal total_testcase, total_success, forest

            self.logger.debug("%s• %s", "  " * depth, node.name)

            configuration = copy.copy(configurations.get(node.name))
            producer = { param: conf for param, conf in configuration.params.items() if conf.type == "ProducerGenerator"}
            producer_mapping = {}
            context_pool.set_current(node.name)

            prefix_groups = defaultdict(set)
            for k, params in node.matched_params.items():
                for p in params:
                    sp = p.get("source_param")
                    if sp:
                        prefix_groups[sp.rsplit(".", 1)[0]].add(k)

            best_prefix = max(prefix_groups, key=lambda x: len(prefix_groups[x]), default=None)
            common_res = None
            for k, producer_obj in producer.items():
                candidates = node.matched_params.get(k)
                if not candidates:
                    continue
                prioritized = [p for p in candidates if best_prefix and p.get("source_param","").startswith(best_prefix)]
                param = random.choice(prioritized or candidates)
                se = param.get("source_endpoint")
                sp = param.get("source_param")
                resource = producer_map.get(se, {}).get(sp)
                resource = resource.split(",")[0] if resource else None
                if parent is not None:
                    if resource and resource not in self.operation_graph.nodes[parent.name].schemas.keys():
                        key = sp.split(".")[-1]
                        if key in self.operation_graph.nodes[parent.name].required_parameters:
                            key = key + ":path"
                        data = {"resource": resource, "key": key, "need_change": True, **param}
                    else:
                        common_res = resource
                        data = {"resource": resource, "key": sp.split(".")[-1], **param}
                else:
                    data = {"resource": resource, "key": sp.split(".")[-1], **param}
                producer_mapping[k] = data
            for k, producer_obj in producer.items():
                if k in producer_mapping:
                    data = producer_mapping[k]
                    if data.get("need_change"):
                        if common_res is not None:
                            data["resource"] = common_res
                        del data["need_change"]
                        producer_mapping[k] = data
                    producer_obj.genParameters = {"pool": [data]}

            emitter.emit(
                EventType.OPERATION_UPDATE,
                phase=Phase.TEST_EXECUTION,
                operation_name=node.name,
                operation_method=node.name.split('-')[0] if '-' in node.name else '',
                operation_path=node.name,
                status=OperationStatus.RUNNING,
            )

            executor = Executor(
                api_url=self.base_url,
                strategy=Strategy.NAIVE_VALUE,
                operation=nodes.get(node.name),
                cache_dir=self.project_dir,
                model=self.model,
                num_test_cases=num_test_cases,
                configuration=configurations.get(node.name),
                mutation_ratio=mutation_ratio,
                header_mutation_ratio=header_mutation_ratio,
                context_pool=context_pool,
                max_request_workers=max_request_workers,
                use_async=True,
                async_max_concurrent=async_max_concurrent,
                default_headers=headers,
            )

            responses = await executor.exec_async()
            feedback = feedback_analyzer.evaluate(seq_path, operation=nodes.get(node.name), responses=responses, producer_mapping=producer_mapping, context_pool=context_pool)
            adjug = feedback_analyzer.adjust(node.name, context_pool, producer_mapping, self.operation_graph, graph_analyst=graph_analyst)
            if adjug and forest_lock:
                async with forest_lock:
                    forest = graph_analyst.export_to_forest()

            success_responses = [
                entry
                for entry in responses if isSuccessful(entry.get("response",{}).get("status",0))
            ]
            context_pool.update_with_responses(success_responses, properties.get(node.name))
            self.logger.debug(
                "Success %s with context_pool %s",
                len(success_responses),
                context_pool,
            )
            total_success += len(success_responses)
            total_testcase += len(responses)
            context_pool.clear_current()

            if len(success_responses) > 0:
                successFull.update({node.name: 1})
                for child in sort_children_by_method(node.children.values()):
                    await _execute_node_async(child, depth + 1, context_pool, node, seq_path + [child.name], forest_lock=forest_lock)

            return responses

        async def _execute_tree_parallel(root_node, tree_context, semaphore, forest_lock):
            """Execute an entire tree with bounded concurrency."""
            async with semaphore:
                self.logger.debug("Root: %s", root_node.name)
                await _execute_node_async(root_node, depth=1, context_pool=tree_context, parent=None, seq_path=[root_node.name], forest_lock=forest_lock)
                return tree_context

        async def traverse_forest_parallel_async(forest, shared_context, max_workers=10):
            """
            Execute forest with parallel root nodes.
            Each root tree runs in parallel (bounded by semaphore).
            Each tree's descendants run sequentially within that tree.
            Results are merged back to shared_context at the end.
            """
            semaphore = asyncio.Semaphore(max_workers)
            forest_lock = asyncio.Lock()
            roots = list(forest.values())

            self.logger.debug(
                "Starting %s trees with max %s concurrent workers",
                len(roots),
                max_workers,
            )

            tasks = []
            for root_node in sort_children_by_method(roots):
                tree_context = shared_context.copy()
                task = _execute_tree_parallel(root_node, tree_context, semaphore, forest_lock)
                tasks.append(task)

            tree_contexts = await asyncio.gather(*tasks)

            self.logger.debug("Merging %s tree contexts", len(tree_contexts))
            for tree_ctx in tree_contexts:
                shared_context.merge(tree_ctx)

            return shared_context

        emitter.emit(EventType.PHASE_START, Phase.TEST_EXECUTION,
                    message=f"Executing tests for {num_generations} generation(s)",
                    total_generations=num_generations)

        for idx in range(num_generations):
            self.logger.debug("Run generation %s/%s", idx + 1, num_generations)

            if async_mode:
                asyncio.run(traverse_forest_parallel_async(
                    forest=forest,
                    shared_context=context,
                    max_workers=max_request_workers or DEFAULT_MAX_REQUEST_WORKERS
                ))
            else:
                traverse_forest_dfs(forest, context)
        if total_testcase == 0:
            self.logger.warning("No test cases executed")
        self.logger.debug(
            "Success rate: %s",
            total_success/total_testcase if total_testcase > 0 else 0,
        )
        self.logger.debug("Successful endpoints map: %s", successFull)
        self.logger.debug("Successful endpoint count: %s", len(successFull.keys()))
        emitter.emit(EventType.PHASE_COMPLETE, Phase.TEST_EXECUTION, message="Test execution complete")
        emitter.emit(EventType.EXECUTION_COMPLETE, Phase.FINAL_REPORT, message="All generations complete")
        return total_testcase, successFull

    
