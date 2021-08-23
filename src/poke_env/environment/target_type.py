# -*- coding: utf-8 -*-
"""This module defines the SideCondition class, which represents a in-battle side
condition.
"""
# pyre-ignore-all-errors[45]
from enum import Enum, unique, auto

# This is an enum for all the target types you can have
@unique
class TargetType(Enum):
    """Enumeration, represent a non null field in a battle."""

    ADJACENT = auto()
    ADJACENT_ALLY_OR_SELF = auto()
    ADJACENT_FOE = auto()
    ALL = auto()
    ALL_ADJACENT = auto()
    ALLIES = auto()
    ALLY_SIDE = auto()
    ALLY_TEAM = auto()
    ANY = auto()
    FOE_SIDE = auto()
    NORMAL = auto()
    RANDOM_NORMAL = auto()
    SCRIPTED = auto()
    SELF = auto()

    def __str__(self) -> str:
        return f"{self.name} (field) object"
