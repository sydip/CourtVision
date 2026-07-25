from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_engine
from app.models import DraftPick, Team

DRAFT_YEAR = 2026
DATA_SOURCE = "user-provided-2026-draft-results"


@dataclass(frozen=True)
class DraftResult:
    overall_pick: int
    player_name: str
    school_country: str
    team_abbreviation: str
    transaction_note: str | None = None

    @property
    def round(self) -> int:
        return 1 if self.overall_pick <= 30 else 2


DRAFT_RESULTS: tuple[DraftResult, ...] = (
    DraftResult(1, "AJ Dybantsa", "BYU", "WAS"),
    DraftResult(2, "Darryn Peterson", "Kansas", "UTA"),
    DraftResult(3, "Cameron Boozer", "Duke", "MEM"),
    DraftResult(4, "Caleb Wilson", "North Carolina", "CHI"),
    DraftResult(5, "Keaton Wagler", "Illinois", "LAC"),
    DraftResult(6, "Mikel Brown Jr.", "Louisville", "BKN"),
    DraftResult(7, "Darius Acuff Jr.", "Arkansas", "SAC"),
    DraftResult(8, "Kingston Flemings", "Houston", "ATL"),
    DraftResult(9, "Morez Johnson Jr.", "Michigan", "DAL"),
    DraftResult(10, "Brayden Burries", "Arizona", "MIL"),
    DraftResult(11, "Yaxel Lendeborg", "Michigan", "GSW"),
    DraftResult(12, "Aday Mara", "Michigan", "OKC"),
    DraftResult(13, "Nate Ament", "Tennessee", "MIL", "traded from Miami"),
    DraftResult(14, "Hannes Steinbach", "Washington", "CHA"),
    DraftResult(15, "Dailyn Swain", "Texas", "CHI", "from Portland"),
    DraftResult(16, "Bennett Stirtz", "Iowa", "OKC", "traded from Memphis"),
    DraftResult(17, "Ebuka Okorie", "Stanford", "DET", "traded via OKC"),
    DraftResult(18, "Christian Anderson Jr.", "Texas Tech", "CHA"),
    DraftResult(19, "Allen Graves", "Santa Clara", "TOR"),
    DraftResult(20, "Jayden Quaintance", "Kentucky", "SAS", "from Atlanta"),
    DraftResult(21, "Karim Lopez", "Mexico", "MEM", "traded from Detroit"),
    DraftResult(22, "Labaron Philon Jr.", "Alabama", "PHI"),
    DraftResult(23, "Zuby Ejiofor", "St. John's", "ATL", "from Cleveland"),
    DraftResult(24, "Cameron Carr", "Baylor", "LAL", "traded from NYK"),
    DraftResult(25, "Sergio de Larrea", "Spain", "DAL", "traded via NYK/LAL"),
    DraftResult(26, "Tarris Reed Jr.", "UConn", "SAS", "traded from Denver"),
    DraftResult(27, "Chris Cenac Jr.", "Houston", "BOS"),
    DraftResult(28, "Joshua Jefferson", "Iowa State", "BKN", "traded from Minnesota"),
    DraftResult(
        29,
        "Alex Karaban",
        "UConn",
        "SAS",
        "traded via Cleveland/Atlanta",
    ),
    DraftResult(
        30,
        "Koa Peat",
        "Arizona",
        "PHX",
        "traded up from Dallas/OKC",
    ),
    DraftResult(31, "Bruce Thornton", "Ohio State", "HOU", "traded from NYK"),
    DraftResult(32, "Richie Saunders", "BYU", "MEM"),
    DraftResult(33, "Isaiah Evans", "Duke", "MIN", "from Brooklyn"),
    DraftResult(34, "Meleek Thomas", "Arkansas", "CLE", "traded from Sacramento"),
    DraftResult(
        35,
        "Trevon Brazile",
        "Arkansas",
        "DEN",
        "traded via San Antonio/Utah",
    ),
    DraftResult(36, "Baba Miller", "Cincinnati", "LAC", "from Memphis"),
    DraftResult(
        37,
        "Ryan Conwell",
        "Louisville",
        "MIA",
        "traded from OKC/Dallas",
    ),
    DraftResult(38, "Braden Smith", "Purdue", "IND", "traded from Chicago"),
    DraftResult(39, "Jack Kayil", "Germany", "NYK", "traded from Houston"),
    DraftResult(40, "Dillon Mitchell", "St. John's", "BOS", "from Milwaukee"),
    DraftResult(41, "Otega Oweh", "Kentucky", "OKC", "traded from Miami"),
    DraftResult(42, "Ja'Kobi Gillespie", "Tennessee", "SAS", "from Portland"),
    DraftResult(43, "Tyler Bilodeau", "UCLA", "BKN", "from LA Clippers"),
    DraftResult(44, "Maliq Brown", "Duke", "SAS", "from Miami"),
    DraftResult(
        45,
        "Emanuel Sharp",
        "Houston",
        "SAC",
        "traded via multiple teams",
    ),
    DraftResult(46, "Felix Okpara", "Tennessee", "WAS", "traded from Orlando"),
    DraftResult(47, "Tyler Nickel", "Vanderbilt", "NYK", "traded from Phoenix"),
    DraftResult(48, "Tobi Lawal", "Virginia Tech", "DAL", "from Phoenix"),
    DraftResult(49, "Bryce Hopkins", "St. John's", "DEN", "from Atlanta"),
    DraftResult(50, "Jaden Bradley", "Arizona", "TOR"),
    DraftResult(
        51,
        "Izaiyah Nelson",
        "South Florida",
        "ORL",
        "traded from Washington",
    ),
    DraftResult(
        52,
        "Henri Veesaar",
        "North Carolina",
        "ATL",
        "traded from Cleveland",
    ),
    DraftResult(
        53,
        "Ugonna Onyenso",
        "Virginia",
        "DET",
        "traded via Houston/NYK",
    ),
    DraftResult(
        54,
        "Lajae Jones",
        "Florida State",
        "GSW",
        "traded from LAL",
    ),
    DraftResult(
        55,
        "Nick Martinelli",
        "Northwestern",
        "LAC",
        "traded via NYK/Houston",
    ),
    DraftResult(
        56,
        "Vsevolod Ishchenko",
        "Russia",
        "DAL",
        "traded via LAL",
    ),
    DraftResult(57, "Narcisse Ngoy", "France", "LAC", "traded from Atlanta"),
    DraftResult(
        58,
        "Jaron Pierre Jr.",
        "SMU",
        "NOP",
        "traded from Detroit",
    ),
    DraftResult(
        59,
        "Trey Kaufman-Renn",
        "Purdue",
        "MIN",
        "traded from San Antonio",
    ),
    DraftResult(
        60,
        "Malique Lewis",
        "Trinidad & Tobago",
        "MIL",
        "traded from Washington",
    ),
)


def ingest_2026_draft_results(session: Session) -> dict[str, int]:
    teams = {
        team.abbreviation: team
        for team in session.scalars(select(Team).order_by(Team.abbreviation)).all()
    }
    missing = sorted(
        {record.team_abbreviation for record in DRAFT_RESULTS}.difference(teams)
    )
    if missing:
        raise ValueError(f"Draft ingestion is missing stored teams: {', '.join(missing)}.")

    inserted = 0
    updated = 0
    for record in DRAFT_RESULTS:
        draft_pick = session.scalar(
            select(DraftPick).where(
                DraftPick.draft_year == DRAFT_YEAR,
                DraftPick.overall_pick == record.overall_pick,
            )
        )
        if draft_pick is None:
            draft_pick = DraftPick(
                draft_year=DRAFT_YEAR,
                overall_pick=record.overall_pick,
                round=record.round,
                player_name=record.player_name,
                school_country=record.school_country,
                team_id=teams[record.team_abbreviation].id,
                transaction_note=record.transaction_note,
                data_source=DATA_SOURCE,
            )
            session.add(draft_pick)
            inserted += 1
        else:
            draft_pick.round = record.round
            draft_pick.player_name = record.player_name
            draft_pick.school_country = record.school_country
            draft_pick.team_id = teams[record.team_abbreviation].id
            draft_pick.transaction_note = record.transaction_note
            draft_pick.data_source = DATA_SOURCE
            updated += 1
    session.flush()
    return {"fetched": len(DRAFT_RESULTS), "inserted": inserted, "updated": updated}


def main() -> None:
    SessionLocal.configure(bind=get_engine())
    with SessionLocal() as session:
        totals = ingest_2026_draft_results(session)
        session.commit()
    print(
        "2026 NBA Draft ingestion complete: "
        f"{totals['inserted']} inserted, {totals['updated']} updated."
    )


if __name__ == "__main__":
    main()
