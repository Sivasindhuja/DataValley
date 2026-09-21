from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class AuthContext:
    authenticated: bool = False
    user_id: Optional[str] = None
    customer_id: Optional[str] = None
    roles: List[str] = field(default_factory=lambda: ["customer"])
    token: Optional[str] = None

    def is_authenticated(self) -> bool:
        return self.authenticated and self.customer_id is not None
