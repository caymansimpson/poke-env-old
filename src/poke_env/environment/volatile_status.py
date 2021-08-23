# -*- coding: utf-8 -*-
"""This module defines the SideCondition class, which represents a in-battle side
condition.
"""
# pyre-ignore-all-errors[45]
from enum import Enum, unique, auto

# This is an enum for all the Volatile Statuses you can have
@unique
class VolatileStatus(Enum):
    """Enumeration, represent a non null field in a battle."""
    AQUA_RING = auto()
    ATTRACT = auto()
    BANEFUL_BUNKER = auto()
    BIDE = auto()
    CHARGE = auto()
    CONFUSION = auto()
    CURSE = auto()
    DEFENSE_CURL = auto()
    DESTINY_BOND = auto()
    DISABLE = auto()
    ELECTRIFY = auto()
    EMBARGO = auto()
    ENDURE = auto()
    FLINCH = auto()
    FOCUS_ENERGY = auto()
    FOLLOW_ME = auto()
    FORESIGHT = auto()
    GASTRO_ACID = auto()
    GRUDGE = auto()
    HEAL_BLOCK = auto()
    HELPING_HAND = auto()
    IMPRISON = auto()
    INGRAIN = auto()
    KINGS_SHIELD = auto()
    LASER_FOCUS = auto()
    LEECH_SEED = auto()
    LOCKED_MOVE = auto()
    MAGIC_COAT = auto()
    MAGNET_RISE = auto()
    MAX_GUARD = auto()
    MINIMIZE = auto()
    MIRACLE_EYE = auto()
    MUST_RECHARGE = auto()
    NIGHTMARE = auto()
    NO_RETREAT = auto()
    OBSTRUCT = auto()
    OCTOLOCK = auto()
    PARTIALLY_TRAPPED = auto()
    POWDER = auto()
    POWER_TRICK = auto()
    PROTECT = auto()
    RAGE = auto()
    RAGE_POWDER = auto()
    ROOST = auto()
    SMACK_DOWN = auto()
    SNATCH = auto()
    SPIKY_SHIELD = auto()
    SPOTLIGHT = auto()
    STOCKPILE = auto()
    SUBSTITUTE = auto()
    TARSHOT = auto()
    TAUNT = auto()
    TELEKINESIS = auto()
    TORMENT = auto()
    UPROAR = auto()
    YAWN = auto()

    def __str__(self) -> str:
        return f"{self.name} (field) object"
