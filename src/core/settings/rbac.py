from pydantic import BaseModel, Field
from typing import Dict, List

class RBACSettings(BaseModel):
    """Role-Based Access Control settings"""
    role_access_matrix: Dict[str, List[str]] = Field(default={
        "employee": ["general"],
        "finance": ["general", "finance"], 
        "engineering": ["general", "engineering"],
        "marketing": ["general", "marketing"],
        "hr": ["general", "hr"],
        "c_level": ["general", "finance", "engineering", "marketing", "hr"]
    })
    
    @property
    def collection_access_roles(self) -> Dict[str, List[str]]:
        """Get which roles can access each collection"""
        access_map = {}
        for role, collections in self.role_access_matrix.items():
            for collection in collections:
                if collection not in access_map:
                    access_map[collection] = []
                access_map[collection].append(role)
        return access_map
