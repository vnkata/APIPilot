import random
import string
from typing import Any, Dict

class ParamsMutator:
    """
    Logic to inject unexpected, undocumented, or malicious parameters 
    into the request to test API robustness and security.
    """

    def __init__(self, rand_inst: random.Random = None):
        self.rand = rand_inst or random.Random()
        
        self.common_security_keys = [
            "admin", "debug", "test", "role", "bypass", "internal", 
            "config", "token", "auth", "is_admin", "user_id", "force"
        ]
        
        self.common_db_fields = [
            "id", "created_at", "updated_at", "deleted_at", "status", "is_deleted"
        ]
        
        self.injection_payloads = [
            "' OR 1=1--",
            "<script>alert(1)</script>",
            "../../etc/passwd",
            "{}",
            "[]",
            "null",
            "undefined"
        ]

    def _random_string(self, length: int = 8) -> str:
        """Generates a random alphanumeric string."""
        return ''.join(self.rand.choices(string.ascii_letters + string.digits, k=length))

    def mutate(self, current_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Injects unexpected keys into the parameter dictionary.
        """
        mutated_params = dict(current_params) if current_params else {}
        
        strategy = self.rand.choice([
            "security_bypass", 
            "mass_assignment", 
            "random_garbage",
            "prototype_pollution",
            "array_confusion"
        ])
        
        if strategy == "security_bypass":
            key = self.rand.choice(self.common_security_keys)
            val = self.rand.choice(["true", "1", "admin", "yes", "on"])
            mutated_params[key] = val
            
        elif strategy == "mass_assignment":
            key = self.rand.choice(self.common_db_fields)
            val = self.rand.choice([1, "9999", "active", "2099-01-01"])
            mutated_params[key] = val
            
        elif strategy == "random_garbage":
            key = self._random_string(self.rand.randint(5, 15))
            val = self.rand.choice([
                self._random_string(), 
                self.rand.randint(1, 1000), 
                self.rand.choice(self.injection_payloads)
            ])
            mutated_params[key] = val
            
        elif strategy == "prototype_pollution":
            mutated_params["__proto__[admin]"] = "true"
            mutated_params["constructor[prototype][is_admin]"] = "1"
            
        elif strategy == "array_confusion":
            if mutated_params:
                existing_key = self.rand.choice(list(mutated_params.keys()))
                mutated_params[existing_key] = [mutated_params[existing_key], self.rand.choice(self.injection_payloads)]

        return mutated_params