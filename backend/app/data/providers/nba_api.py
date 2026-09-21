from __future__ import annotations

import importlib
import socket
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal, Protocol, TypeAlias, cast

from app.data.raw_cache import JsonPayload, RawResponseCache
from app.data.source_schemas import (
    SourceGame,
    SourceLeaguePlayerStatistic,
    SourcePlayer,
    SourcePlayerGameLog,
    SourcePlayerProfile,
    SourceStanding,
    SourceTeam,
    SourceTeamGameLog,
)

RawMapping: TypeAlias = Mapping[str, object]
EASTERN_TEAM_ABBREVIATIONS = frozenset(
    {
        "ATL",
        "BOS",
        "BKN",
        "CHA",
        "CHI",
        "CLE",
        "DET",
        "IND",
        "MIA",
        "MIL",
        "NYK",
        "ORL",
        "PHI",
        "TOR",
        "WAS",
    }
)
RawFetcher: TypeAlias = Callable[[], JsonPayload]
RawValidator: TypeAlias = Callable[[JsonPayload], None]
EndpointFactory: TypeAlias = Callable[..., "NormalizedEndpoint"]


class NormalizedEndpoint(Protocol):
    def get_normalized_dict(self) -> JsonPayload: ...


class NbaApiProviderError(RuntimeError):
    pass


class NbaApiRequestError(NbaApiProviderError):
    pass


class NbaApiTimeoutError(NbaApiRequestError):
    pass


class NbaApiRateLimitError(NbaApiRequestError):
    pass


class MalformedProviderResponseError(NbaApiProviderError):
    pass


class ProviderUnavailableError(NbaApiProviderError):
    pass


class NbaApiClientProtocol(Protocol):
    def get_static_players(self) -> JsonPayload: ...

    def get_static_teams(self) -> JsonPayload: ...

    def get_common_player_info(self, player_id: int, timeout_seconds: float) -> JsonPayload: ...

    def get_player_game_log(
        self,
        player_id: int,
        season: str,
        timeout_seconds: float,
    ) -> JsonPayload: ...

    def get_league_player_game_log(self, season: str, timeout_seconds: float) -> JsonPayload: ...

    def get_league_player_stats(
        self,
        season: str,
        measure_type: str,
        timeout_seconds: float,
    ) -> JsonPayload: ...

    def get_league_team_game_log(self, season: str, timeout_seconds: float) -> JsonPayload: ...

    def get_league_team_stats(self, season: str, timeout_seconds: float) -> JsonPayload: ...


class NbaApiClient:
    def get_static_players(self) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.static.players")
        get_players = cast(Callable[[], JsonPayload], module.__dict__["get_players"])
        return get_players()

    def get_static_teams(self) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.static.teams")
        get_teams = cast(Callable[[], JsonPayload], module.__dict__["get_teams"])
        return get_teams()

    def get_common_player_info(self, player_id: int, timeout_seconds: float) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.endpoints.commonplayerinfo")
        endpoint_factory = cast(EndpointFactory, module.__dict__["CommonPlayerInfo"])
        endpoint = endpoint_factory(
            player_id=player_id,
            timeout=timeout_seconds,
        )
        return endpoint.get_normalized_dict()

    def get_player_game_log(
        self,
        player_id: int,
        season: str,
        timeout_seconds: float,
    ) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.endpoints.playergamelog")
        endpoint_factory = cast(EndpointFactory, module.__dict__["PlayerGameLog"])
        date_from, date_to = _season_date_range(season)
        endpoint = endpoint_factory(
            player_id=player_id,
            season=season,
            date_from_nullable=date_from,
            date_to_nullable=date_to,
            timeout=timeout_seconds,
        )
        return endpoint.get_normalized_dict()

    def get_league_player_game_log(self, season: str, timeout_seconds: float) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.endpoints.leaguegamelog")
        endpoint_factory = cast(EndpointFactory, module.__dict__["LeagueGameLog"])
        endpoint = endpoint_factory(
            player_or_team_abbreviation="P",
            season=season,
            season_type_all_star="Regular Season",
            timeout=timeout_seconds,
        )
        return endpoint.get_normalized_dict()

    def get_league_player_stats(
        self,
        season: str,
        measure_type: str,
        timeout_seconds: float,
    ) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.endpoints.leaguedashplayerstats")
        endpoint_factory = cast(EndpointFactory, module.__dict__["LeagueDashPlayerStats"])
        endpoint = endpoint_factory(
            season=season,
            measure_type_detailed_defense=measure_type,
            per_mode_detailed="PerGame",
            timeout=timeout_seconds,
        )
        return endpoint.get_normalized_dict()

    def get_league_team_game_log(self, season: str, timeout_seconds: float) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.endpoints.leaguegamelog")
        endpoint_factory = cast(EndpointFactory, module.__dict__["LeagueGameLog"])
        endpoint = endpoint_factory(
            player_or_team_abbreviation="T",
            season=season,
            season_type_all_star="Regular Season",
            timeout=timeout_seconds,
        )
        return endpoint.get_normalized_dict()

    def get_league_team_stats(self, season: str, timeout_seconds: float) -> JsonPayload:
        module = importlib.import_module("nba_api.stats.endpoints.leaguedashteamstats")
        endpoint_factory = cast(EndpointFactory, module.__dict__["LeagueDashTeamStats"])
        endpoint = endpoint_factory(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            timeout=timeout_seconds,
        )
        return endpoint.get_normalized_dict()


class NbaApiProvider:
    def __init__(
        self,
        *,
        season: str,
        raw_data_dir: str,
        timeout_seconds: float,
        player_ids: Sequence[int] | None = None,
        player_limit: int | None = 1,
        max_retries: int = 2,
        backoff_seconds: float = 1.0,
        request_delay_seconds: float = 0.6,
        roster_source: Literal["active", "season"] = "active",
        game_log_source: Literal["per_player", "league"] = "per_player",
        client: NbaApiClientProtocol | None = None,
        sleep_func: Callable[[float], None] = time.sleep,
    ) -> None:
        if player_limit is not None and player_limit < 1:
            raise ValueError("player_limit must be at least 1 when provided.")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative.")
        self.season = season
        self.raw_cache = RawResponseCache(raw_data_dir)
        self.timeout_seconds = timeout_seconds
        self.player_ids = list(player_ids or [])
        self.player_limit = player_limit
        self.roster_source = roster_source
        self.game_log_source = game_log_source
        self._bulk_game_logs: dict[int, list[RawMapping]] | None = None
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.request_delay_seconds = request_delay_seconds
        self.client = client or NbaApiClient()
        self.sleep_func = sleep_func
        self._request_count = 0
        self._raw_memory: dict[str, JsonPayload] = {}
        self._teams_by_abbreviation: dict[str, SourceTeam] | None = None

    def get_teams(self) -> list[SourceTeam]:
        raw = self._load_raw(
            "static_teams",
            self.client.get_static_teams,
            _validate_static_list("static_teams"),
        )
        teams: list[SourceTeam] = []
        for row in _ensure_mapping_rows(raw, "static_teams"):
            teams.append(
                SourceTeam(
                    nba_team_id=_required_int(row, "id"),
                    abbreviation=_required_str(row, "abbreviation"),
                    city=_normalized_team_city(row),
                    name=_required_str(row, "nickname", fallback_key="name"),
                )
            )
        return teams

    def get_players(self) -> list[SourcePlayer]:
        raw = self._load_raw(
            "static_players",
            self.client.get_static_players,
            _validate_static_list("static_players"),
        )
        rows = _ensure_mapping_rows(raw, "static_players")
        static_by_id: dict[int, RawMapping] = {}
        for row in rows:
            player_id = _optional_int(row, "id")
            if player_id is not None:
                static_by_id[player_id] = row

        team_ids_by_player_id = self._team_ids_by_player_id()
        selected_ids = self._select_player_ids(rows, static_by_id, team_ids_by_player_id)

        players: list[SourcePlayer] = []
        for player_id in selected_ids:
            static_row = static_by_id.get(player_id)
            if static_row is None:
                # Present in the season's league stats but absent from the static index
                # (very rare); skip rather than fabricate identity fields.
                continue
            full_name = _required_str(static_row, "full_name")
            players.append(
                SourcePlayer(
                    nba_player_id=player_id,
                    slug=_slugify(f"{full_name}-{player_id}"),
                    full_name=full_name,
                    first_name=_optional_str(static_row, "first_name"),
                    last_name=_optional_str(static_row, "last_name"),
                    team_nba_id=team_ids_by_player_id.get(player_id),
                )
            )
        return players

    def _select_player_ids(
        self,
        static_rows: list[RawMapping],
        static_by_id: dict[int, RawMapping],
        team_ids_by_player_id: dict[int, int],
    ) -> list[int]:
        if self.player_ids:
            return list(self.player_ids)

        if self.roster_source == "season":
            # Roster is every player who actually appeared in the selected season, taken
            # from that season's league statistics rather than today's active flag.
            ordered = sorted(
                team_ids_by_player_id.keys(),
                key=lambda pid: (_optional_str(static_by_id.get(pid, {}), "full_name") or "", pid),
            )
            if self.player_limit is not None:
                ordered = ordered[: self.player_limit]
            return ordered

        active_rows = [row for row in static_rows if _optional_bool(row, "is_active") is not False]
        active_rows = sorted(active_rows, key=lambda row: _optional_str(row, "full_name") or "")
        if self.player_limit is not None:
            active_rows = active_rows[: self.player_limit]
        return [
            player_id
            for row in active_rows
            if (player_id := _optional_int(row, "id")) is not None
        ]

    def get_player_profiles(self) -> list[SourcePlayerProfile]:
        profiles: list[SourcePlayerProfile] = []
        for player_id in self._target_player_ids():
            endpoint = f"common_player_info_{player_id}"

            def fetch_profile(player_id: int = player_id) -> JsonPayload:
                return self.client.get_common_player_info(player_id, self.timeout_seconds)

            raw = self._load_raw(
                endpoint,
                fetch_profile,
                _validate_dataset(endpoint, "CommonPlayerInfo"),
            )
            rows = _dataset_rows(raw, "CommonPlayerInfo", endpoint)
            if not rows:
                raise MalformedProviderResponseError(f"{endpoint} returned no player profile rows.")
            row = rows[0]
            profiles.append(
                SourcePlayerProfile(
                    nba_player_id=_optional_int(row, "PERSON_ID") or player_id,
                    birthdate=_optional_date(row, "BIRTHDATE"),
                    height=_optional_str(row, "HEIGHT"),
                    weight_pounds=_optional_int(row, "WEIGHT"),
                    position=_optional_str(row, "POSITION"),
                    jersey_number=_optional_str(row, "JERSEY"),
                    active=(_optional_str(row, "ROSTERSTATUS") or "").lower() != "inactive",
                )
            )
        return profiles

    def get_games(self) -> list[SourceGame]:
        games_by_id: dict[str, SourceGame] = {}
        teams_by_abbreviation = self._get_teams_by_abbreviation()
        for player_id in self._target_player_ids():
            for row in self._player_game_log_rows(player_id):
                matchup = _required_str(row, "MATCHUP")
                game_id = _required_str(row, "Game_ID", fallback_key="GAME_ID")
                team_abbreviation, home_abbreviation, away_abbreviation = _parse_matchup(matchup)
                if team_abbreviation not in teams_by_abbreviation:
                    raise MalformedProviderResponseError(
                        f"Unknown team abbreviation in matchup: {team_abbreviation}"
                    )
                if home_abbreviation not in teams_by_abbreviation:
                    raise MalformedProviderResponseError(
                        f"Unknown home team abbreviation in matchup: {home_abbreviation}"
                    )
                if away_abbreviation not in teams_by_abbreviation:
                    raise MalformedProviderResponseError(
                        f"Unknown away team abbreviation in matchup: {away_abbreviation}"
                    )
                games_by_id[game_id] = SourceGame(
                    nba_game_id=game_id,
                    season=self.season,
                    game_date=_required_date(row, "GAME_DATE"),
                    home_team_nba_id=teams_by_abbreviation[home_abbreviation].nba_team_id,
                    away_team_nba_id=teams_by_abbreviation[away_abbreviation].nba_team_id,
                )
        return list(games_by_id.values())

    def get_season_game_logs(self, season: str) -> list[SourcePlayerGameLog]:
        if season != self.season:
            raise ValueError(f"Provider was configured for {self.season}, not {season}.")
        teams_by_abbreviation = self._get_teams_by_abbreviation()
        logs: list[SourcePlayerGameLog] = []
        for player_id in self._target_player_ids():
            for row in self._player_game_log_rows(player_id):
                matchup = _required_str(row, "MATCHUP")
                team_abbreviation, _, _ = _parse_matchup(matchup)
                team = teams_by_abbreviation.get(team_abbreviation)
                _, home_abbreviation, _ = _parse_matchup(matchup)
                logs.append(
                    SourcePlayerGameLog(
                        nba_player_id=_optional_int(row, "Player_ID") or player_id,
                        nba_game_id=_required_str(row, "Game_ID", fallback_key="GAME_ID"),
                        team_nba_id=team.nba_team_id if team else None,
                        season=season,
                        matchup=matchup,
                        is_home=team_abbreviation == home_abbreviation,
                        result=_optional_result(row, "WL"),
                        minutes=_optional_decimal_minutes(row, "MIN"),
                        points=_int_or_zero(row, "PTS"),
                        rebounds=_int_or_zero(row, "REB"),
                        assists=_int_or_zero(row, "AST"),
                        steals=_int_or_zero(row, "STL"),
                        blocks=_int_or_zero(row, "BLK"),
                        turnovers=_int_or_zero(row, "TOV"),
                        personal_fouls=_int_or_zero(row, "PF"),
                        field_goals_made=_int_or_zero(row, "FGM"),
                        field_goals_attempted=_int_or_zero(row, "FGA"),
                        three_pointers_made=_int_or_zero(row, "FG3M"),
                        three_pointers_attempted=_int_or_zero(row, "FG3A"),
                        free_throws_made=_int_or_zero(row, "FTM"),
                        free_throws_attempted=_int_or_zero(row, "FTA"),
                        plus_minus=_optional_decimal(row, "PLUS_MINUS"),
                    )
                )
        return logs

    def get_league_player_statistics(self, season: str) -> list[SourceLeaguePlayerStatistic]:
        if season != self.season:
            raise ValueError(f"Provider was configured for {self.season}, not {season}.")
        base_rows = self._league_player_stat_rows("Base")
        advanced_rows = self._league_player_stat_rows("Advanced")
        advanced_by_player_id = {
            _required_int(row, "PLAYER_ID"): row
            for row in advanced_rows
            if _optional_int(row, "PLAYER_ID") is not None
        }

        selected_ids = set(self.player_ids) if self.player_ids else None
        summaries: list[SourceLeaguePlayerStatistic] = []
        for row in base_rows:
            player_id = _required_int(row, "PLAYER_ID")
            if selected_ids is not None and player_id not in selected_ids:
                continue
            advanced = advanced_by_player_id.get(player_id, {})
            summaries.append(
                SourceLeaguePlayerStatistic(
                    nba_player_id=player_id,
                    team_nba_id=_optional_int(row, "TEAM_ID"),
                    season=season,
                    games_played=_int_or_zero(row, "GP"),
                    minutes_per_game=_optional_decimal(row, "MIN"),
                    points_per_game=_optional_decimal(row, "PTS"),
                    rebounds_per_game=_optional_decimal(row, "REB"),
                    assists_per_game=_optional_decimal(row, "AST"),
                    true_shooting_percentage=_optional_rate(advanced, "TS_PCT"),
                    usage_rate=_optional_rate(advanced, "USG_PCT"),
                )
            )
            if selected_ids is None and self.player_limit is not None:
                if len(summaries) >= self.player_limit:
                    break
        return summaries

    def get_team_game_logs(self, season: str) -> list[SourceTeamGameLog]:
        if season != self.season:
            raise ValueError(f"Provider was configured for {self.season}, not {season}.")
        endpoint = f"league_team_game_log_{season}"
        raw = self._load_raw(
            endpoint,
            lambda: self.client.get_league_team_game_log(season, self.timeout_seconds),
            _validate_dataset(endpoint, "LeagueGameLog"),
        )
        rows = _dataset_rows(raw, "LeagueGameLog", endpoint)
        points_by_game_team = {
            (_required_str(row, "GAME_ID"), _required_int(row, "TEAM_ID")): _int_or_zero(row, "PTS")
            for row in rows
        }
        teams_by_abbreviation = self._get_teams_by_abbreviation()
        results: list[SourceTeamGameLog] = []
        for row in rows:
            matchup = _required_str(row, "MATCHUP")
            team_abbreviation, home_abbreviation, away_abbreviation = _parse_matchup(matchup)
            opponent_abbreviation = (
                away_abbreviation if team_abbreviation == home_abbreviation else home_abbreviation
            )
            opponent = teams_by_abbreviation[opponent_abbreviation]
            game_id = _required_str(row, "GAME_ID")
            results.append(
                SourceTeamGameLog(
                    nba_team_id=_required_int(row, "TEAM_ID"),
                    nba_game_id=game_id,
                    season=season,
                    is_home=team_abbreviation == home_abbreviation,
                    points=_int_or_zero(row, "PTS"),
                    opponent_points=points_by_game_team[(game_id, opponent.nba_team_id)],
                    result=_required_str(row, "WL"),
                )
            )
        return results

    def get_standings(self, season: str) -> list[SourceStanding]:
        if season != self.season:
            raise ValueError(f"Provider was configured for {self.season}, not {season}.")
        endpoint = f"league_team_stats_{season}"
        raw = self._load_raw(
            endpoint,
            lambda: self.client.get_league_team_stats(season, self.timeout_seconds),
            _validate_dataset(endpoint, "LeagueDashTeamStats"),
        )
        rows = _dataset_rows(raw, "LeagueDashTeamStats", endpoint)
        # LeagueDashTeamStats identifies teams by TEAM_ID; the TEAM_ABBREVIATION column is
        # not always present (e.g. some historical seasons), so resolve via id.
        teams_by_id = {team.nba_team_id: team for team in self.get_teams()}
        grouped: dict[str, list[tuple[SourceTeam, RawMapping]]] = {"East": [], "West": []}
        for row in rows:
            team_id = _optional_int(row, "TEAM_ID")
            team = teams_by_id.get(team_id) if team_id is not None else None
            if team is None:
                # Skip league-average or otherwise unrecognized aggregate rows.
                continue
            conference = "East" if team.abbreviation in EASTERN_TEAM_ABBREVIATIONS else "West"
            grouped[conference].append((team, row))
        results: list[SourceStanding] = []
        for conference, entries in grouped.items():
            ordered = sorted(
                entries,
                key=lambda entry: (-_int_or_zero(entry[1], "W"), _int_or_zero(entry[1], "L")),
            )
            for rank, (team, row) in enumerate(ordered, start=1):
                results.append(
                    SourceStanding(
                        nba_team_id=team.nba_team_id,
                        season=season,
                        conference=conference,
                        rank=rank,
                        wins=_int_or_zero(row, "W"),
                        losses=_int_or_zero(row, "L"),
                        win_pct=_optional_decimal(row, "W_PCT") or Decimal(0),
                    )
                )
        return results

    def _target_player_ids(self) -> list[int]:
        if self.player_ids:
            return list(self.player_ids)
        return [player.nba_player_id for player in self.get_players()]

    def _get_teams_by_abbreviation(self) -> dict[str, SourceTeam]:
        if self._teams_by_abbreviation is None:
            self._teams_by_abbreviation = {team.abbreviation: team for team in self.get_teams()}
        return self._teams_by_abbreviation

    def _team_ids_by_player_id(self) -> dict[int, int]:
        team_ids: dict[int, int] = {}
        try:
            rows = self._league_player_stat_rows("Base")
        except ProviderUnavailableError:
            return team_ids
        for row in rows:
            player_id = _optional_int(row, "PLAYER_ID")
            team_id = _optional_int(row, "TEAM_ID")
            if player_id is not None and team_id is not None:
                team_ids[player_id] = team_id
        return team_ids

    def _player_game_log_rows(self, player_id: int) -> list[RawMapping]:
        if self.game_log_source == "league":
            return self._bulk_player_game_log_rows().get(player_id, [])

        endpoint = f"player_game_log_{self.season}_{player_id}"

        def fetch_game_log(player_id: int = player_id) -> JsonPayload:
            return self.client.get_player_game_log(player_id, self.season, self.timeout_seconds)

        raw = self._load_raw(
            endpoint,
            fetch_game_log,
            _validate_dataset(endpoint, "PlayerGameLog"),
        )
        return _dataset_rows(raw, "PlayerGameLog", endpoint)

    def _bulk_player_game_log_rows(self) -> dict[int, list[RawMapping]]:
        """Fetch the entire season's player game logs in a single league-wide request.

        The per-player ``PlayerGameLog`` path costs one network call per player
        (hundreds per season). ``LeagueGameLog`` returns every player's logs at once,
        so this groups that single response by player id and reuses it thereafter.
        """
        if self._bulk_game_logs is None:
            endpoint = f"league_player_game_log_{self.season}"
            raw = self._load_raw(
                endpoint,
                lambda: self.client.get_league_player_game_log(self.season, self.timeout_seconds),
                _validate_dataset(endpoint, "LeagueGameLog"),
            )
            rows = _dataset_rows(raw, "LeagueGameLog", endpoint)
            grouped: dict[int, list[RawMapping]] = {}
            for row in rows:
                player_id = _optional_int(row, "PLAYER_ID")
                if player_id is not None:
                    grouped.setdefault(player_id, []).append(row)
            self._bulk_game_logs = grouped
        return self._bulk_game_logs

    def _league_player_stat_rows(self, measure_type: str) -> list[RawMapping]:
        endpoint = f"league_player_stats_{self.season}_{measure_type.lower()}"

        def fetch_league_stats(measure_type: str = measure_type) -> JsonPayload:
            return self.client.get_league_player_stats(
                self.season,
                measure_type,
                self.timeout_seconds,
            )

        raw = self._load_raw(
            endpoint,
            fetch_league_stats,
            _validate_dataset(endpoint, "LeagueDashPlayerStats"),
        )
        return _dataset_rows(raw, "LeagueDashPlayerStats", endpoint)

    def _load_raw(
        self,
        endpoint: str,
        fetcher: RawFetcher,
        validator: RawValidator,
    ) -> JsonPayload:
        if endpoint in self._raw_memory:
            return self._raw_memory[endpoint]

        try:
            raw = self._fetch_with_retries(endpoint, fetcher)
            validator(raw)
            self.raw_cache.save(self.season, endpoint, raw)
            self._raw_memory[endpoint] = raw
            return raw
        except NbaApiProviderError as exc:
            cached = self.raw_cache.load_latest(self.season, endpoint)
            if cached is None:
                raise ProviderUnavailableError(
                    f"{endpoint} failed and no cached response is available: {exc}"
                ) from exc
            validator(cached)
            self._raw_memory[endpoint] = cached
            return cached

    def _fetch_with_retries(self, endpoint: str, fetcher: RawFetcher) -> JsonPayload:
        last_error: NbaApiProviderError | None = None
        for attempt in range(self.max_retries + 1):
            try:
                self._delay_before_request()
                return fetcher()
            except Exception as exc:
                last_error = _wrap_request_error(endpoint, exc)
                if attempt >= self.max_retries:
                    break
                self.sleep_func(self.backoff_seconds * (2**attempt))
        if last_error is None:
            raise NbaApiRequestError(f"{endpoint} failed without an exception.")
        raise last_error

    def _delay_before_request(self) -> None:
        if self._request_count > 0 and self.request_delay_seconds > 0:
            self.sleep_func(self.request_delay_seconds)
        self._request_count += 1


def _validate_static_list(endpoint: str) -> RawValidator:
    def validator(raw: JsonPayload) -> None:
        _ensure_mapping_rows(raw, endpoint)

    return validator


def _validate_dataset(endpoint: str, dataset_name: str) -> RawValidator:
    def validator(raw: JsonPayload) -> None:
        _dataset_rows(raw, dataset_name, endpoint)

    return validator


def _ensure_mapping_rows(raw: JsonPayload, endpoint: str) -> list[RawMapping]:
    if not isinstance(raw, list):
        raise MalformedProviderResponseError(f"{endpoint} must be a JSON array.")
    rows: list[RawMapping] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise MalformedProviderResponseError(f"{endpoint} contains a non-object row.")
        rows.append(cast(RawMapping, item))
    return rows


def _dataset_rows(raw: JsonPayload, dataset_name: str, endpoint: str) -> list[RawMapping]:
    if not isinstance(raw, Mapping):
        raise MalformedProviderResponseError(f"{endpoint} must be a JSON object.")
    dataset = raw.get(dataset_name)
    if not isinstance(dataset, list):
        raise MalformedProviderResponseError(f"{endpoint} missing list dataset {dataset_name}.")
    rows: list[RawMapping] = []
    for item in dataset:
        if not isinstance(item, Mapping):
            raise MalformedProviderResponseError(f"{endpoint}.{dataset_name} has a non-object row.")
        rows.append(cast(RawMapping, item))
    return rows


def _wrap_request_error(endpoint: str, exc: Exception) -> NbaApiProviderError:
    if isinstance(exc, NbaApiProviderError):
        return exc
    status_code = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None),
        "status_code",
        None,
    )
    message = str(exc)
    lowered = message.lower()
    if status_code == 429 or "429" in lowered or "rate limit" in lowered:
        return NbaApiRateLimitError(f"{endpoint} was rate limited: {message}")
    if isinstance(exc, TimeoutError | socket.timeout) or "timeout" in lowered:
        return NbaApiTimeoutError(f"{endpoint} timed out: {message}")
    return NbaApiRequestError(f"{endpoint} request failed: {message}")


def _required_str(row: RawMapping, key: str, *, fallback_key: str | None = None) -> str:
    value = row.get(key)
    if value is None and fallback_key is not None:
        value = row.get(fallback_key)
    if value is None or str(value).strip() == "":
        raise MalformedProviderResponseError(f"Missing required field {key}.")
    return str(value).strip()


def _normalized_team_city(row: RawMapping) -> str:
    abbreviation = _required_str(row, "abbreviation")
    city = _required_str(row, "city")
    name = _required_str(row, "nickname", fallback_key="name")
    if abbreviation == "GSW" and city == "San Francisco" and name == "Warriors":
        return "Golden State"
    return city


def _optional_str(row: RawMapping, key: str) -> str | None:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def _required_int(row: RawMapping, key: str) -> int:
    value = _optional_int(row, key)
    if value is None:
        raise MalformedProviderResponseError(f"Missing required integer field {key}.")
    return value


def _optional_int(row: RawMapping, key: str) -> int | None:
    value = row.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if not isinstance(value, str | float | Decimal):
        raise MalformedProviderResponseError(f"Invalid integer field {key}: {value}")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MalformedProviderResponseError(f"Invalid integer field {key}: {value}") from exc


def _int_or_zero(row: RawMapping, key: str) -> int:
    return _optional_int(row, key) or 0


def _optional_bool(row: RawMapping, key: str) -> bool | None:
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "active"}


def _optional_result(row: RawMapping, key: str) -> str | None:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    result = str(value).strip().upper()
    if result not in {"W", "L"}:
        raise MalformedProviderResponseError(f"Invalid win/loss result field {key}: {value}")
    return result


def _required_date(row: RawMapping, key: str) -> date:
    value = _optional_date(row, key)
    if value is None:
        raise MalformedProviderResponseError(f"Missing required date field {key}.")
    return value


def _optional_date(row: RawMapping, key: str) -> date | None:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    raw = str(value).strip()
    parsers: tuple[Callable[[str], date], ...] = (
        _parse_iso_date,
        _parse_abbreviated_month_date,
        _parse_full_month_date,
        _parse_date_only,
    )
    for parser in parsers:
        try:
            return parser(raw)
        except ValueError:
            continue
    raise MalformedProviderResponseError(f"Invalid date field {key}: {value}")


def _parse_iso_date(value: str) -> date:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).date()


def _parse_abbreviated_month_date(value: str) -> date:
    return datetime.strptime(value, "%b %d, %Y").date()


def _parse_full_month_date(value: str) -> date:
    return datetime.strptime(value, "%B %d, %Y").date()


def _parse_date_only(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _season_date_range(season: str) -> tuple[str, str]:
    """Return an explicit MM/DD/YYYY window covering a season's games.

    Without explicit bounds, stats.nba.com's PlayerGameLog endpoint can
    silently collapse to a single recent game for players whose most recent
    logged game falls outside whatever default window it infers, dropping
    the rest of their season. Passing a wide, explicit range avoids that.
    """
    start_year = int(season[:4])
    end_year = start_year + 1
    return f"10/01/{start_year}", f"06/30/{end_year}"


def _optional_decimal(row: RawMapping, key: str) -> Decimal | None:
    value = row.get(key)
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MalformedProviderResponseError(f"Invalid decimal field {key}: {value}") from exc


def _optional_decimal_minutes(row: RawMapping, key: str) -> Decimal | None:
    value = row.get(key)
    if isinstance(value, str) and ":" in value:
        minutes, seconds = value.split(":", 1)
        try:
            return Decimal(minutes) + (Decimal(seconds) / Decimal(60))
        except (InvalidOperation, ValueError) as exc:
            raise MalformedProviderResponseError(f"Invalid minute field {key}: {value}") from exc
    return _optional_decimal(row, key)


def _optional_rate(row: RawMapping, key: str) -> Decimal | None:
    value = _optional_decimal(row, key)
    if value is None:
        return None
    if value > 1 and value <= 100:
        return value / Decimal(100)
    return value


def _parse_matchup(matchup: str) -> tuple[str, str, str]:
    parts = matchup.replace("vs.", "vs").split()
    if len(parts) < 3:
        raise MalformedProviderResponseError(f"Invalid matchup: {matchup}")
    team_abbreviation = parts[0]
    marker = parts[1]
    opponent_abbreviation = parts[2]
    if marker == "@":
        return team_abbreviation, opponent_abbreviation, team_abbreviation
    if marker.lower() == "vs":
        return team_abbreviation, team_abbreviation, opponent_abbreviation
    raise MalformedProviderResponseError(f"Invalid matchup location marker: {matchup}")


def _slugify(value: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in value)
    return "-".join(part for part in slug.split("-") if part)
