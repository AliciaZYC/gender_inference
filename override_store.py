"""
Abstract persistence layer for gender overrides
Supports dependency injection for different storage backends
"""

from typing import Optional, Dict
from abc import ABC, abstractmethod


class OverrideStore(ABC):
    """Abstract persistence layer interface for gender overrides"""
    
    @abstractmethod
    def get_override(self, athlete_id: str) -> Optional[str]:
        """
        Get stored gender override for an athlete
        Returns: 'male', 'female', or None if no override exists
        """
        raise NotImplementedError
    
    @abstractmethod
    def set_override(self, athlete_id: str, gender: str):
        """
        Store a gender override for an athlete
        Args:
            athlete_id: Unique identifier for the athlete
            gender: 'male' or 'female'
        """
        raise NotImplementedError
    
    @abstractmethod
    def clear_override(self, athlete_id: str):
        """
        Remove gender override for an athlete
        Args:
            athlete_id: Unique identifier for the athlete
        """
        raise NotImplementedError


class InMemoryOverrideStore(OverrideStore):
    """
    In-memory implementation for testing
    Data is lost when program exits
    """
    
    def __init__(self):
        self._store: Dict[str, str] = {}
    
    def get_override(self, athlete_id: str) -> Optional[str]:
        """Get override from memory"""
        return self._store.get(athlete_id)
    
    def set_override(self, athlete_id: str, gender: str):
        """Store override in memory"""
        normalized_gender = gender.lower().strip()
        if normalized_gender not in ['male', 'female']:
            raise ValueError(f"Invalid gender: {gender}. Must be 'male' or 'female'")
        self._store[athlete_id] = normalized_gender
    
    def clear_override(self, athlete_id: str):
        """Remove override from memory"""
        if athlete_id in self._store:
            del self._store[athlete_id]
    
    def get_all_overrides(self) -> Dict[str, str]:
        """Get all stored overrides (for debugging)"""
        return self._store.copy()


# Future implementations can be added here:
# class MongoDBOverrideStore(OverrideStore):
#     """MongoDB-backed implementation"""
#     ...
#
# class RedisOverrideStore(OverrideStore):
#     """Redis-backed implementation"""
#     ...

