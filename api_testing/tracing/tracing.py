import base64
import json
import logging
import os
import litellm  

trace_path = None  # Set this to your desired trace directory path
usages = {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0,
}

def _llm_cost_tracking_(kwargs, response_obj, start_time, end_time):
    global trace_path, usages
    # log callback to fils
    print("✅ on_success_callback triggered!")
    # global usages
    current_usage = response_obj.get("usage", {})
    current_usage = {
        "prompt_tokens": current_usage.get("prompt_tokens", 0),
        "completion_tokens": current_usage.get("completion_tokens", 0),
        "total_tokens": current_usage.get("total_tokens", 0)
    }
    usages["prompt_tokens"] += current_usage["prompt_tokens"]
    usages["completion_tokens"] += current_usage["completion_tokens"]
    usages["total_tokens"] += current_usage["total_tokens"]
    # save global usages to file
    try:
        with open(trace_path + "/llm_usage.json", "w", encoding="utf-8") as f:
            json.dump(usages, f, ensure_ascii=False, indent=4)  
        print(f"[TraceManager] Updated LLM usage in {trace_path}")
    except Exception as e:
        print(f"[TraceManager] Error updating LLM usage: {e}")
    # Details
    try:
        with open(trace_path + "/llm_response.jsonl", "a", encoding="utf-8") as f:
            response_data = {
                "messages": kwargs.get("messages"),
                "usage": current_usage,
                "time": (end_time - start_time).total_seconds()
            }
            json.dump(response_data, f, ensure_ascii=False)
            f.write("\n")
        print(f"[TraceManager] Logged response to {trace_path}")
    except Exception as e:
        print(f"[TraceManager] Error logging response: {e}")
   

def init_trace_manager(trace_path_param):
    global trace_path
    trace_path = trace_path_param
    # 2️⃣ Register globally before making any requests
    litellm.success_callback = [_llm_cost_tracking_]

def setup_logger(redirect_to_dev_log=False):
    global trace_path
    """Set up a logger to log to both file and console within the main_path."""
    logger_name = 'WebPilotAgent'
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:  # Avoid adding handlers multiple times
        # Create a file handler for writing logs to a file
        log_filename = 'agent.log'
        f_handler = logging.FileHandler(os.path.join(trace_path, log_filename), encoding="utf-8")
        f_handler.setLevel(logging.INFO)
        # Create a console handler for printing logs to the terminal
        c_handler = logging.StreamHandler()
        c_handler.setLevel(logging.INFO)
        # Create formatters for file and console handlers
        file_formatter = logging.Formatter('%(asctime)s - %(message)s')
        console_formatter = logging.Formatter('%(message)s')
        # Set formatters for file and console handlers
        f_handler.setFormatter(file_formatter)
        c_handler.setFormatter(console_formatter)
        # Add the handlers to the logger
        logger.addHandler(f_handler)
        if not redirect_to_dev_log:  # Only add console handler if not redirecting to dev log
            logger.addHandler(c_handler)
    return logger

class TraceManager:
    def __init__(self, trace_path=None):
        self.tracing = None
        self.trace_path = trace_path # Directory to save trace files, e.g., "/results/<task_id>"
        # os.makedirs(self.trace_path, exist_ok=True)

    def _cost_tracking_(self, kwargs, response_obj, start_time, end_time):
        print("✅ on_success_callback triggered!")
        print("Model used:", kwargs.get("model"))
        print("Response:", response_obj)
        
    def _setup_logger(self, redirect_to_dev_log=False):
        """Set up a logger to log to both file and console within the main_path."""
        logger_name = 'WebPilotAgent'
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:  # Avoid adding handlers multiple times
            # Create a file handler for writing logs to a file
            log_filename = 'agent.log'
            f_handler = logging.FileHandler(os.path.join(self.trace_path, log_filename), encoding="utf-8")
            f_handler.setLevel(logging.INFO)

            # Create a console handler for printing logs to the terminal
            c_handler = logging.StreamHandler()
            c_handler.setLevel(logging.INFO)

            # Create formatters for file and console handlers
            file_formatter = logging.Formatter('%(asctime)s - %(message)s')
            console_formatter = logging.Formatter('%(message)s')

            # Set formatters for file and console handlers
            f_handler.setFormatter(file_formatter)
            c_handler.setFormatter(console_formatter)

            # Add the handlers to the logger
            logger.addHandler(f_handler)
            if not redirect_to_dev_log:  # Only add console handler if not redirecting to dev log
                logger.addHandler(c_handler)

        return logger
    # Capture the DOM tree
    def _capture_dom_trace(self, dom_data, filename="dom_trace.html"):
        """Capture DOM data to an HTML file in the trace_path directory."""
        if self.trace_path is None:
            raise ValueError("Trace path is not set. Please set trace_path before capturing traces.")
        
        dom_file_path = os.path.join(self.trace_path, filename)
        with open(dom_file_path, 'w', encoding='utf-8') as f:
            f.write(dom_data)
    # Capture the Accessibility Tree
    def _capture_a11y_trace(self, a11y_data, filename="a11y_trace.json"):
        """Capture accessibility data to a JSON file in the trace_path directory."""
        if self.trace_path is None:
            raise ValueError("Trace path is not set. Please set trace_path before capturing traces.")
        
        a11y_file_path = os.path.join(self.trace_path, filename)
        with open(a11y_file_path, 'w', encoding='utf-8') as f:
            f.write(a11y_data)

    # Capture the Screenshot as PNG
    def _capture_screenshot_trace(self, screenshot_data, filename="screenshot.png"):
        """Capture screenshot data to a PNG file in the trace_path directory."""
        if self.trace_path is None:
            raise ValueError("Trace path is not set. Please set trace_path before capturing traces.")
        
        screenshot_file_path = os.path.join(self.trace_path, filename)
        with open(screenshot_file_path, 'wb') as f:
            f.write(base64.b64decode(screenshot_data))
            
    def _capture_trace(self, trace_data, filename="trace.json"):
        """Capture trace data to a JSON file in the trace_path directory."""
        if self.trace_path is None:
            raise ValueError("Trace path is not set. Please set trace_path before capturing traces.")
        
        trace_file_path = os.path.join(self.trace_path, filename)
        with open(trace_file_path, 'w', encoding='utf-8') as f:
            f.write(trace_data) 