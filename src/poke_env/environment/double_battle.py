# -*- coding: utf-8 -*-

from logging import Logger
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from poke_env.environment.abstract_battle import AbstractBattle
from poke_env.environment.move import Move
from poke_env.environment.pokemon import Pokemon
from poke_env.environment.pokemon_type import PokemonType
from poke_env.environment.move import SPECIAL_MOVES
from poke_env.environment.move_category import MoveCategory


class DoubleBattle(AbstractBattle):
    POKEMON_1_POSITION = -1
    POKEMON_2_POSITION = -2
    OPPONENT_1_POSITION = 1
    OPPONENT_2_POSITION = 2
    EMPTY_TARGET_POSITION = 0  # symbolic, not used by showdown

    def __init__(self, battle_tag: str, username: str, logger: Logger):
        super(DoubleBattle, self).__init__(battle_tag, username, logger)

        # Turn choice attributes
        self._available_moves: List[List[Move]] = [[], []]
        self._available_switches: List[List[Pokemon]] = [[], []]
        self._can_mega_evolve: List[bool] = [False, False]
        self._can_z_move: List[bool] = [False, False]
        self._can_dynamax: List[bool] = [False, False]
        self._opponent_can_dynamax: List[bool] = [True, True]
        self._force_switch: List[bool] = [False, False]
        self._maybe_trapped: List[bool] = [False, False]
        self._trapped: List[bool] = [False, False]

        # Battle state attributes
        self._active_pokemon: Dict[str, Pokemon] = {}
        self._opponent_active_pokemon: Dict[str, Pokemon] = {}

        # Other
        self._move_to_pokemon_id: Dict[Move, str] = {}
        self._sent_team: Set[Pokemon] = set() # To account who we sent, useful for VGC

    def _clear_all_boosts(self):
        for active_pokemon_group in (self.active_pokemon, self.opponent_active_pokemon):
            for active_pokemon in active_pokemon_group:
                if active_pokemon is not None:
                    active_pokemon._clear_boosts()

    def _end_illusion(self, pokemon_name: str, details: str):
        player_identifier = pokemon_name[:2]
        pokemon_identifier = pokemon_name[:3]
        if player_identifier == self._player_role:
            active_dict = self._active_pokemon
        else:
            active_dict = self._opponent_active_pokemon
        active = active_dict.get(pokemon_identifier)

        active_dict[pokemon_identifier] = self._end_illusion_on(
            illusioned=active, illusionist=pokemon_name, details=details
        )

    @staticmethod
    def _get_active_pokemon(
        active_pokemon: Dict[str, Pokemon], role: str
    ) -> List[Optional[Pokemon]]:
        pokemon_1 = active_pokemon.get(f"{role}a")
        pokemon_2 = active_pokemon.get(f"{role}b")
        if pokemon_1 is None or not pokemon_1.active or pokemon_1.fainted:
            pokemon_1 = None
        if pokemon_2 is None or not pokemon_2.active or pokemon_2.fainted:
            pokemon_2 = None
        return [pokemon_1, pokemon_2]

    def _parse_request(self, request: Dict) -> None:
        """
        Update the object from a request.
        The player's pokemon are all updated, as well as available moves, switches and
        other related information (z move, mega evolution, forced switch...).
        Args:
            request (dict): parsed json request object
        """
        self.logger.debug(
            "Parsing the following request update in battle %s:\n%s",
            self.battle_tag,
            request,
        )

        if "wait" in request and request["wait"]:
            self._wait = True
        else:
            self._wait = False

        self._available_moves = [[], []]
        self._available_switches = [[], []]
        self._can_mega_evolve = [False, False]
        self._can_z_move = [False, False]
        self._can_dynamax = [False, False]
        self._maybe_trapped = [False, False]
        self._trapped = [False, False]
        self._force_switch = request.get("forceSwitch", [False, False])

        if any(self._force_switch):
            self._move_on_next_request = True

        if request["rqid"]:
            self._rqid = max(self._rqid, request["rqid"])

        if request.get("teamPreview", False):
            self._teampreview = True
            number_of_mons = len(request["side"]["pokemon"])
            self._max_team_size = request.get("maxTeamSize", number_of_mons)
        else:
            self._teampreview = False

        side = request["side"]
        if side["pokemon"]:
            self._player_role = side["pokemon"][0]["ident"][:2]
        self._update_team_from_request(side)

        if "active" in request:
            for active_pokemon_number, active_request in enumerate(request["active"]):
                pokemon_dict = request["side"]["pokemon"][active_pokemon_number]
                active_pokemon = self.get_pokemon(
                    pokemon_dict["ident"],
                    force_self_team=True,
                    details=pokemon_dict["details"],
                )
                if self.player_role is not None:
                    if (
                        active_pokemon_number == 0
                        and f"{self.player_role}a" not in self._active_pokemon
                    ):
                        self._active_pokemon[f"{self.player_role}a"] = active_pokemon
                    elif f"{self.player_role}b" not in self._active_pokemon:
                        self._active_pokemon[f"{self.player_role}b"] = active_pokemon

                if active_pokemon.fainted:
                    continue

                if active_request.get("trapped"):
                    self._trapped[active_pokemon_number] = True

                self._available_moves[
                    active_pokemon_number
                ] = active_pokemon.available_moves_from_request(active_request)

                if active_request.get("canMegaEvo", False):
                    self._can_mega_evolve[active_pokemon_number] = True
                if active_request.get("canZMove", False):
                    self._can_z_move[active_pokemon_number] = True
                if active_request.get("canDynamax", False):
                    self._can_dynamax[active_pokemon_number] = True
                if active_request.get("maybeTrapped", False):
                    self._maybe_trapped[active_pokemon_number] = True

        for pokemon_index, trapped in enumerate(self.trapped):
            if (not trapped) or self.force_switch[pokemon_index]:
                for pokemon in side["pokemon"]:
                    if pokemon:
                        pokemon = self._team[pokemon["ident"]]
                        if not pokemon.active and not pokemon.fainted:
                            self._available_switches[pokemon_index].append(pokemon)

        # To account for who we sent (useful for VGC)
        self._sent_team = set(map(lambda x: self._team[x['ident']], side['pokemon']))

    def _switch(self, pokemon, details, hp_status):
        pokemon_identifier = pokemon.split(":")[0][:3]
        player_identifier = pokemon_identifier[:2]
        team = (
            self._active_pokemon
            if player_identifier == self._player_role
            else self._opponent_active_pokemon
        )
        pokemon_out = team.pop(pokemon_identifier, None)
        if pokemon_out is not None:
            pokemon_out._switch_out()
        pokemon_in = self.get_pokemon(pokemon, details=details)
        pokemon_in._switch_in()
        pokemon_in._set_hp_status(hp_status)
        team[pokemon_identifier] = pokemon_in

    def _swap(self, pokemon, slot):
        player_identifier = pokemon.split(":")[0][:2]
        team = (
            self._active_pokemon
            if player_identifier == self.player_role
            else self._opponent_active_pokemon
        )
        slot_a = f"{player_identifier}a"
        slot_b = f"{player_identifier}b"

        if team[slot_a].fainted or team[slot_b].fainted:
            return

        slot_a_mon = team[slot_a]
        slot_b_mon = team[slot_b]

        pokemon = self.get_pokemon(pokemon)

        if (slot == "0" and pokemon == slot_a_mon) or (
            slot == "1" and pokemon == slot_b_mon
        ):
            pass
        else:
            team[slot_a], team[slot_b] = team[slot_b], team[slot_a]

    def get_possible_showdown_targets(
        self, move: Move, pokemon: Pokemon, dynamax=False
    ) -> List[int]:
        """
        Given move of an ALLY Pokemon, returns a list of possible Pokemon Showdown
        targets for it. This is smart enough so that it figures whether the Pokemon
        is already dynamaxed.

        :param move: Move instance for which possible targets should be returned
        :type move: Move
        :param dynamax: whether given move also STARTS dynamax for its user
        :return: a list of integers indicating Pokemon Showdown targets:
            -1, -2, 1, 2 or self.EMPTY_TARGET_POSITION that indicates "no target"
        :rtype: List[int]
        """
        if move.id in SPECIAL_MOVES:
            return [self.EMPTY_TARGET_POSITION]

        pokemon_1, pokemon_2 = self.active_pokemon
        if pokemon == pokemon_1 and move in self.available_moves[0]:
            self_position = self.POKEMON_1_POSITION
            ally_position = self.POKEMON_2_POSITION
        elif pokemon == pokemon_2 and move in self.available_moves[1]:
            self_position = self.POKEMON_2_POSITION
            ally_position = self.POKEMON_1_POSITION
        else:
            raise Exception(
                f"Selected move {move.id} is not owned by any active ally Pokemon "
                f"that is currently battling"
            )

        if dynamax or pokemon.is_dynamaxed:
            if move.category == MoveCategory.STATUS:
                targets = [self.EMPTY_TARGET_POSITION]
            else:
                targets = [self.OPPONENT_1_POSITION, self.OPPONENT_2_POSITION]
        elif move.non_ghost_target and (
            PokemonType.GHOST not in pokemon.types
        ):  # fixing target for Curse
            return [self.EMPTY_TARGET_POSITION]
        else:
            targets = {
                "adjacentAlly": [ally_position],
                "adjacentAllyOrSelf": [ally_position, self_position],
                "adjacentFoe": [self.OPPONENT_1_POSITION, self.OPPONENT_2_POSITION],
                "all": [self.EMPTY_TARGET_POSITION],
                "allAdjacent": [self.EMPTY_TARGET_POSITION],
                "allAdjacentFoes": [self.EMPTY_TARGET_POSITION],
                "allies": [self.EMPTY_TARGET_POSITION],
                "allySide": [self.EMPTY_TARGET_POSITION],
                "allyTeam": [self.EMPTY_TARGET_POSITION],
                "any": [
                    ally_position,
                    self.OPPONENT_1_POSITION,
                    self.OPPONENT_2_POSITION,
                ],
                "foeSide": [self.EMPTY_TARGET_POSITION],
                "normal": [
                    ally_position,
                    self.OPPONENT_1_POSITION,
                    self.OPPONENT_2_POSITION,
                ],
                "randomNormal": [self.EMPTY_TARGET_POSITION],
                "scripted": [self.EMPTY_TARGET_POSITION],
                "self": [self.EMPTY_TARGET_POSITION],
                self.EMPTY_TARGET_POSITION: [self.EMPTY_TARGET_POSITION],
                None: [self.OPPONENT_1_POSITION, self.OPPONENT_2_POSITION],
            }[move.deduced_target]

        pokemon_ids = set(self._opponent_active_pokemon.keys())
        pokemon_ids.update(self._active_pokemon.keys())
        targets_to_keep = {
            {
                f"{self.player_role}a": -1,
                f"{self.player_role}b": -2,
                f"{self.opponent_role}a": 1,
                f"{self.opponent_role}b": 2,
            }[pokemon_identifier]
            for pokemon_identifier in pokemon_ids
        }
        targets_to_keep.add(self.EMPTY_TARGET_POSITION)
        targets = [target for target in targets if target in targets_to_keep]

        return targets

    @property
    def active_pokemon(self) -> List[Optional[Pokemon]]:
        """
        :return: The active pokemon, always at least one is not None
        :rtype: List[Optional[Pokemon]]
        """
        if self.player_role is None:
            raise ValueError("Unable to get active_pokemon, player_role is None")
        return self._get_active_pokemon(
            self._active_pokemon, self.player_role  # pyre-ignore
        )

    @property
    def all_active_pokemons(self) -> List[Optional[Pokemon]]:
        """
        :return: A list containing all active pokemons and/or Nones.
        :rtype: List[Optional[Pokemon]]
        """
        return [*self.active_pokemon, *self.opponent_active_pokemon]

    @property
    def available_moves(self) -> List[List[Move]]:
        """
        :return: A list of two lists of moves the player can use during the current
            move request for each Pokemon.
        :rtype: List[List[Move]]
        """
        return self._available_moves

    @property
    def available_switches(self) -> List[List[Pokemon]]:
        """
        :return: The list of two lists of switches the player can do during the
            current move request for each active pokemon
        :rtype: List[List[Pokemon]]
        """
        return self._available_switches

    @property
    def can_dynamax(self) -> List[bool]:
        """
        :return: Wheter or not the current active pokemon can dynamax
        :rtype: List[bool]
        """
        return self._can_dynamax

    @property
    def can_mega_evolve(self) -> List[bool]:
        """
        :return: Whether of not either current active pokemon can mega evolve.
        :rtype: List[bool]
        """
        return self._can_mega_evolve

    @property
    def can_z_move(self) -> List[bool]:
        """
        :return: Wheter of not the current active pokemon can z-move.
        :rtype: List[bool]
        """
        return self._can_z_move

    @property
    def force_switch(self) -> List[bool]:
        """
        :return: A boolean indicating whether the active pokemon is forced
            to switch out.
        :rtype: List[bool]
        """
        return self._force_switch

    @property
    def maybe_trapped(self) -> List[bool]:
        """
        :return: A boolean indicating whether either active pokemon is maybe trapped
            by the opponent.
        :rtype: List[bool]
        """
        return self._maybe_trapped

    @property
    def opponent_active_pokemon(self) -> List[Optional[Pokemon]]:
        """
        :return: The opponent active pokemon, always at least one is not None
        :rtype: List[Optional[Pokemon]]
        """
        if self.opponent_role is None:
            raise ValueError(
                "Unable to get opponent_active_pokemon, opponent_role is None"
            )
        return self._get_active_pokemon(
            self._opponent_active_pokemon, self.opponent_role  # pyre-ignore
        )

    @property
    def opponent_can_dynamax(self) -> List[bool]:
        """
        :return: Wheter of not opponent's current active pokemon can dynamax
        :rtype: List[bool]
        """
        return self._opponent_can_dynamax

    @opponent_can_dynamax.setter
    def opponent_can_dynamax(self, value: Union[bool, List[bool]]) -> None:
        if isinstance(value, bool):
            self._opponent_can_dynamax = [value, value]
        else:
            self._opponent_can_dynamax = value

    @property
    def sent_team(self) -> Dict[str, Pokemon]:
        """
        A dict of mons that we sent out for the battle (different from self.team) in
        the case of VGC, where we only send out a portion of our team.

        :return: The full team we sent. Keys are identifiers, values are pokemon objects.
            This includes all mons that are possible
        :rtype: Dict[str, Pokemon]
        """
        return {mon.species: mon for mon in self._sent_team}

    @property
    def teampreview_opponent_team(self) -> Dict[str, Pokemon]:
        """
        During teampreview, keys are not definitive: please rely on values; self.team
        only stores what we currently know of an opponent's team, which is little in
        some cases in VGC; this property returns everything we see in team preview.

        :return: The opponent's full team. Keys are identifiers, values are pokemon objects.
            This includes all mons that are possible
        :rtype: Dict[str, Pokemon]
        """
        return {mon.species: mon for mon in self._teampreview_opponent_team}
    @property
    def trapped(self) -> List[bool]:
        """
        :return: A boolean indicating whether either active pokemon is trapped by the
            opponent.
        :rtype: List[bool]
        """
        return self._trapped

    @trapped.setter
    def trapped(self, value: List[bool]):
        self._trapped = value
