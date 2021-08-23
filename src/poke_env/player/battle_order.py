# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Optional, Union, List
from poke_env.environment.double_battle import DoubleBattle
from poke_env.environment.move import Move
from poke_env.environment.pokemon import Pokemon


@dataclass
class BattleOrder:
    order: Optional[Union[Move, Pokemon]]
    actor: Optional[Pokemon] = None
    mega: bool = False
    z_move: bool = False
    dynamax: bool = False
    # Represents the showdown target
    move_target: int = DoubleBattle.EMPTY_TARGET_POSITION

    DEFAULT_ORDER = "/choose default"

    def __str__(self) -> str:
        return self.message

    @property
    def message(self) -> str:
        if isinstance(self.order, Move):
            if self.order.id == "recharge":  # pyre-ignore
                return "/choose move 1"

            message = f"/choose move {self.order.id}"
            if self.mega:
                message += " mega"
            elif self.z_move:
                message += " zmove"
            elif self.dynamax:
                message += " dynamax"

            if self.move_target != DoubleBattle.EMPTY_TARGET_POSITION:
                message += f" {self.move_target}"
            return message
        else:
            return f"/choose switch {self.order.species}"  # pyre-ignore

    def is_move(self) -> bool:
        """
        :return: Whether this action represents a move. If empty, will return False
        :rtype: bool
        """
        return isinstance(self.order, Move)

    def is_switch(self) -> bool:
        """
        :return: Whether this action represents a switch. If empty, will return False
        :rtype: bool
        """
        return isinstance(self.order, Pokemon)

    def is_empty(self) -> bool:
        """
        :return: Whether the Action has been set to anything, or is an empty action (default)
        :rtype: bool
        """
        return not (self.order or self.actor)

    # Returns list of showdown targets, and None if there are no other affected mons
    @staticmethod
    def get_affected_targets(battle, order) -> List[int]:
        if not order.is_move: return None

        potentials = []
        if order.move_target == DoubleBattle.EMPTY_TARGET_POSITION:

            # Add all pokemon who could be affected for moves like Surf or Earthquake
            if order.order.deduced_target == 'allAdjacent':
                for i, potential_mon in enumerate(battle.active_pokemon):
                    if potential_mon is not None and order.actor != potential_mon:
                        potentials.append(DoubleBattle.active_pokemon_to_showdown_target(i, opp=False))

                for i, potential_mon in enumerate(battle.opponent_active_pokemon):
                    if potential_mon is not None: potentials.append(DoubleBattle.active_pokemon_to_showdown_target(i, opp=True))

            # For moves like Heatwave that affect all opponents, ensure that we list all potential affected opponents
            elif order.order.deduced_target in ['foeSide', 'allAdjacentFoes']:
                for i, potential_mon in enumerate(battle.opponent_active_pokemon):
                    if potential_mon: potentials.append(DoubleBattle.active_pokemon_to_showdown_target(i, opp=True))

            # For moves that affect our side of the field
            elif order.order.deduced_target in ['allies', 'allySide', 'allyTeam']:
                for i, potential_mon in enumerate(battle.active_pokemon):
                    if potential_mon and mon != potential_mon: potentials.append(DoubleBattle.active_pokemon_to_showdown_target(i, opp=True))

            # For moves that don't have targets (like self-moves)
            else:
                return None

        else:
            # If this is a one-target move, and there is one pokemon left, technically both opponent targets work in Showdown, since there's only one valid
            # target. For our purposes, we only want to return the right target (where the mon is) so that we can retrieve the mon later without hassle
            if battle.showdown_target_to_mon(order.move_target):
                potentials.append(order.move_target)
            elif order.move_target < 0:
                raise("get_affected_targets has been given an invalid order where we're targeting an ally... but there's no ally...?")
            else:
                raise("targeting an empty slot with a one mon move... though its on the opponents side")

        return potentials

class DefaultBattleOrder(BattleOrder):
    first_order: Optional[BattleOrder] = None
    second_order: Optional[BattleOrder] = None

    def __init__(self, *args, **kwargs):
        pass

    @property
    def message(self) -> str:
        return self.DEFAULT_ORDER

    def __str__(self) -> str:
        return f"'{self.message}'"

@dataclass
class DoubleBattleOrder(BattleOrder):
    def __init__(
        self,
        first_order: Optional[BattleOrder] = None,
        second_order: Optional[BattleOrder] = None,
    ):
        self.first_order = first_order
        self.second_order = second_order

    @property
    def message(self) -> str:
        if self.first_order and self.second_order:
            return (
                self.first_order.message  # pyre-ignore
                + ", "
                + self.second_order.message.replace("/choose ", "")
            )
        elif self.first_order:
            return self.first_order.message + ", default"
        elif self.second_order:
            return self.second_order.message + ", default"
        else:
            return self.DEFAULT_ORDER

    def __str__(self) -> str:
        first_actor = self.first_order.actor if self.first_order and self.first_order.actor else "None"
        second_actor = self.second_order.actor if self.second_order and self.second_order.actor else "None"
        return f"'{self.message}' by {first_actor}, {second_actor}"

    @staticmethod
    def is_valid(battle, double_order, v=None):

        if battle.active_pokemon[0] and not double_order.first_order:
            if v: print("ERROR: First Pokemon exists and we didn't send an order for it")
            return False

        if not battle.active_pokemon[0] and double_order.first_order:
            if v: print("ERROR: First Pokemon doesn't exists and we sent an order for it")
            return False

        if battle.active_pokemon[1] and not double_order.second_order:
            if v: print("ERROR: Second Pokemon exists and we didn't send an order for it")
            return False

        if not battle.active_pokemon[1] and double_order.second_order:
            if v: print("ERROR: Second Pokemon doesn't exists and we sent an order for it")
            return False

        if double_order.first_order and battle.active_pokemon[0] and double_order.first_order.is_move() and double_order.first_order.order not in battle.available_moves[0]:
            if v: print("ERROR: First Pokemon doesn't have the requested move available to use")
            return False

        if double_order.second_order and battle.active_pokemon[1] and double_order.second_order.is_move() and double_order.second_order.order not in battle.available_moves[1]:
            if v: print("ERROR: Second Pokemon doesn't have the requested move available to use")
            return False

        if double_order.first_order and double_order.first_order.dynamax and not battle.can_dynamax[0]:
            if v: print("ERROR: First Pokemon can't Dynamax")
            return False

        if double_order.second_order and double_order.second_order.dynamax and not battle.can_dynamax[1]:
            if v: print("ERROR: Second Pokemon can't Dynamax")
            return False

        if double_order.first_order and double_order.first_order.actor and double_order.first_order.actor.is_dynamaxed and double_order.first_order.dynamax:
            if v: print("ERROR: First Pokemon is already Dynamax")
            return False

        if double_order.second_order and double_order.second_order.actor and double_order.second_order.actor.is_dynamaxed and double_order.second_order.dynamax:
            if v: print("ERROR: Second Pokemon is already Dynamax")
            return False

        if all(battle.force_switch):
            if not (double_order.first_order and double_order.second_order and double_order.first_order.is_switch() and double_order.second_order.is_switch()):
                if v: print("ERROR: Two Switches Requested, but <2 returned")
                return False

        elif any(battle.force_switch):
            if not((double_order.first_order and double_order.first_order.is_switch() and not double_order.second_order) or (not double_order.first_order and double_order.second_order and double_order.second_order.is_switch())):
                if v: print("ERROR: One switch requested, and != 1 returned")
                return False

        elif double_order.first_order and double_order.second_order and not all(battle.active_pokemon):
            if v: print("ERROR: Two Moves requested, but only one active mon")
            return False

        elif double_order.first_order and double_order.second_order:
            if double_order.first_order.mega and double_order.second_order.mega:
                if v: print("ERROR: Two Mega evolutions attempted")
                return False
            if double_order.first_order.z_move and double_order.second_order.z_move:
                if v: print("ERROR: Two Z-Moves attempted")
                return False
            if double_order.first_order.dynamax and double_order.second_order.dynamax:
                if v: print("ERROR: Two Dynamaxes attempted")
                return False
            if double_order.first_order.order == double_order.second_order.order and double_order.first_order.is_switch() and double_order.second_order.is_switch():
                if v: print("ERROR: Two Switches Requested to the same Pokemon")
                return False

        # Iterate through orders for the errors that could happen within a single order
        for i, order in enumerate([double_order.first_order, double_order.second_order]):

            if order and order.is_switch() and battle.trapped[i]:
                if v: print(f"ERROR:  {i}th Pokemon requested to Switch, but it's trapped")
                return False

            if order and order.is_move() and order.move_target != 0:
                if not battle.showdown_target_to_mon(order.move_target):
                    if v: print(f"ERROR: {i}th Pokemon tried to target a Pokemon that doesn't exist")
                    return False

            if order and order.is_move() and order.actor and (order.actor.is_dynamaxed or order.dynamax):

                if order.move_target < 0:
                    if v: print(f"ERROR: {i}th Pokemon can't target your own Pokemon when dynamaxed")
                    return False

                if (order.order.damage or order.order.base_power > 0) and order.move_target <= 0:
                    if v: print(f"ERROR: {i}th Pokemon has to choose a target for damaging moves when dynamaxed")
                    return False

        return True


    @staticmethod
    def join_orders(first_orders, second_orders):
        if first_orders and second_orders:
            orders = [
                DoubleBattleOrder(first_order=first_order, second_order=second_order)
                for first_order in first_orders
                for second_order in second_orders
                if not first_order.mega or not second_order.mega
                if not first_order.z_move or not second_order.z_move
                if not first_order.dynamax or not second_order.dynamax
                if first_order.order != second_order.order
            ]
            if orders:
                return orders
        elif first_orders:
            return [DoubleBattleOrder(first_order=order) for order in first_orders]
        elif second_orders:
            return [DoubleBattleOrder(first_order=order) for order in second_orders]
        return [DefaultBattleOrder()]


class ForfeitBattleOrder(BattleOrder):
    def __init__(self, *args, **kwargs):
        pass

    @property
    def message(self) -> str:
        return "/forfeit"
