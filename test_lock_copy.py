import copy
import threading

class MyClass:
    def __init__(self):
        self.lock = threading.Lock()

try:
    obj = MyClass()
    copy.deepcopy(obj)
    print("Success")
except Exception as e:
    print(f"Error: {type(e).__name__} - {e}")
