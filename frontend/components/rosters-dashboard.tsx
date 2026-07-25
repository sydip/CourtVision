"use client";

import type { CSSProperties, MutableRefObject } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AppShell } from "@/components/app-shell";
import { PlayerNumberMark } from "@/components/player-number-mark";
import {
  getAllPlayers,
  getDataStatus,
  getPlayer,
  getPlayerSummary,
  getTeams,
} from "@/lib/api/hoopsiq";
import type {
  DataStatus,
  PlayerDetail,
  PlayerListItem,
  PlayerSeasonSummary,
  Team,
} from "@/lib/api/schemas";

/* eslint-disable @next/next/no-img-element */

type ConferenceFilter = "all" | "East" | "West";

type RosterMode = "teams" | "roster";
type RosterTab = "overview" | "players";

type RosterPlayer = {
  detail: PlayerDetail | undefined;
  isTwoWay: boolean;
  player: PlayerListItem;
  summary: PlayerSeasonSummary | undefined;
};

type StarPlayer = {
  player: PlayerListItem;
  summary: PlayerSeasonSummary | undefined;
};

type TeamHistory = {
  era: string;
  overview: string;
  highlights: string[];
};

type TeamFacts = {
  arena: string;
  founded: string;
  location: string;
  nickname: string;
  owner: string;
};

type TeamSnapshot = {
  avgAge: number | null;
  avgMpg: number | null;
  capSpace: number;
  capUsed: number;
  payroll: number;
  rosterCount: number;
};

type TeamTheme = {
  primary: string;
  accent: string;
  glow: string;
  muted: string;
  border: string;
};

type TeamLogoMotif =
  | "antler"
  | "bear"
  | "bridge"
  | "bull"
  | "claw"
  | "compass"
  | "crown"
  | "flame"
  | "gear"
  | "hawk"
  | "hornet"
  | "horse"
  | "liberty"
  | "lightning"
  | "monument"
  | "mountain"
  | "net"
  | "note"
  | "pelican"
  | "rocket"
  | "shamrock"
  | "skyline"
  | "speed"
  | "spur"
  | "star"
  | "sun"
  | "sunset"
  | "sword"
  | "trail"
  | "wolf";

const defaultSelectedTeamId = 1610612744;
const positionOrder = ["Guard", "Guard-Forward", "Forward", "Forward-Center", "Center", "Unlisted"];

const teamThemes: Record<number, TeamTheme> = {
  1610612737: theme("#e03a3e", "#fdb927"),
  1610612738: theme("#007a33", "#ba9653"),
  1610612739: theme("#6f263d", "#ffb81c"),
  1610612740: theme("#0c2340", "#b4975a"),
  1610612741: theme("#ce1141", "#ffffff"),
  1610612742: theme("#00538c", "#b8c4ca"),
  1610612743: theme("#0e2240", "#fec524"),
  1610612744: theme("#1d428a", "#ffc72c"),
  1610612745: theme("#ce1141", "#c4ced4"),
  1610612746: theme("#c8102e", "#1d428a"),
  1610612747: theme("#552583", "#fdb927"),
  1610612748: theme("#98002e", "#f9a01b"),
  1610612749: theme("#00471b", "#eee1c6"),
  1610612750: theme("#0c2340", "#236192"),
  1610612751: theme("#111827", "#ffffff"),
  1610612752: theme("#006bb6", "#f58426"),
  1610612753: theme("#0077c0", "#c4ced4"),
  1610612754: theme("#002d62", "#fdbb30"),
  1610612755: theme("#006bb6", "#ed174c"),
  1610612756: theme("#1d1160", "#e56020"),
  1610612757: theme("#e03a3e", "#ffffff"),
  1610612758: theme("#5a2d81", "#63727a"),
  1610612759: theme("#111827", "#c4ced4"),
  1610612760: theme("#007ac1", "#ef3b24"),
  1610612761: theme("#ce1141", "#753bbd"),
  1610612762: theme("#753bbd", "#9bd8ff"),
  1610612763: theme("#5d76a9", "#f5b112"),
  1610612764: theme("#002b5c", "#e31837"),
  1610612765: theme("#c8102e", "#1d42ba"),
  1610612766: theme("#00788c", "#1d1160"),
};

const defaultTheme = theme("#4f83ff", "#8fb2ff");

const teamLogoMotifs: Record<number, TeamLogoMotif> = {
  1610612737: "hawk",
  1610612738: "shamrock",
  1610612739: "sword",
  1610612740: "pelican",
  1610612741: "bull",
  1610612742: "horse",
  1610612743: "mountain",
  1610612744: "bridge",
  1610612745: "rocket",
  1610612746: "compass",
  1610612747: "sunset",
  1610612748: "flame",
  1610612749: "antler",
  1610612750: "wolf",
  1610612751: "net",
  1610612752: "skyline",
  1610612753: "star",
  1610612754: "speed",
  1610612755: "liberty",
  1610612756: "sun",
  1610612757: "trail",
  1610612758: "crown",
  1610612759: "spur",
  1610612760: "lightning",
  1610612761: "claw",
  1610612762: "note",
  1610612763: "bear",
  1610612764: "monument",
  1610612765: "gear",
  1610612766: "hornet",
};

const teamOwners: Record<number, string> = {
  1610612737: "Tony Ressler",
  1610612738: "Bill / William Chisholm",
  1610612739: "Dan Gilbert",
  1610612740: "Gayle Benson",
  1610612741: "Jerry Reinsdorf",
  1610612742: "Adelson and Dumont families",
  1610612743: "Ann Walton Kroenke / Kroenke Sports & Entertainment",
  1610612744: "Joe Lacob and Peter Guber",
  1610612745: "Tilman Fertitta",
  1610612746: "Steve Ballmer",
  1610612747: "Mark Walter",
  1610612748: "Micky Arison",
  1610612749: "Wes Edens, Jimmy Haslam, and Dee Haslam",
  1610612750: "Marc Lore and Alex Rodriguez",
  1610612751: "Joe Tsai and Clara Wu Tsai",
  1610612752: "James Dolan / Madison Square Garden Sports",
  1610612753: "Dan DeVos / DeVos family",
  1610612754: "Herbert Simon",
  1610612755: "Josh Harris and David Blitzer",
  1610612756: "Mat Ishbia and Justin Ishbia",
  1610612757: "Tom Dundon",
  1610612758: "Vivek Ranadive",
  1610612759: "Peter J. Holt / Holt family",
  1610612760: "Clay Bennett / Professional Basketball Club LLC",
  1610612761: "Rogers Communications and Larry Tanenbaum / MLSE",
  1610612762: "Ryan Smith, Ashley Smith, and ownership group",
  1610612763: "Robert Pera",
  1610612764: "Ted Leonsis / Monumental Sports & Entertainment",
  1610612765: "Tom Gores",
  1610612766: "Gabe Plotkin and Rick Schnall",
};

const headCoachesByTeam: Record<number, string> = {
  1610612737: "Quin Snyder",
  1610612738: "Joe Mazzulla",
  1610612739: "Kenny Atkinson",
  1610612740: "Jamahl Mosley",
  1610612741: "Tiago Splitter",
  1610612742: "Dusty May",
  1610612743: "David Adelman",
  1610612744: "Steve Kerr",
  1610612745: "Ime Udoka",
  1610612746: "Tyronn Lue",
  1610612747: "JJ Redick",
  1610612748: "Erik Spoelstra",
  1610612749: "Taylor Jenkins",
  1610612750: "Chris Finch",
  1610612751: "Jordi Fernandez",
  1610612752: "Mike Brown",
  1610612753: "Sean Sweeney",
  1610612754: "Rick Carlisle",
  1610612755: "Nick Nurse",
  1610612756: "Jordan Ott",
  1610612757: "Micah Nori",
  1610612758: "Doug Christie",
  1610612759: "Mitch Johnson",
  1610612760: "Mark Daigneault",
  1610612761: "Darko Rajakovic",
  1610612762: "Will Hardy",
  1610612763: "Tuomas Iisalo",
  1610612764: "Brian Keefe",
  1610612765: "J.B. Bickerstaff",
  1610612766: "Charles Lee",
};

const teamHistories: Record<number, TeamHistory> = {
  1610612737: history(
    "1946 roots, Atlanta since 1968",
    "The Hawks trace back through Tri-Cities, Milwaukee, and St. Louis before becoming Atlanta's NBA franchise. Their history features Bob Pettit, Dominique Wilkins, Dikembe Mutombo, and modern guard-led teams.",
    ["1958 NBA champions", "Dominique Wilkins era", "Modern guard-led rebuild"],
  ),
  1610612738: history(
    "Original NBA franchise",
    "The Celtics are one of basketball's historic powers, shaped by Red Auerbach, Bill Russell, Larry Bird, Paul Pierce, and modern championship cores.",
    ["Russell-era dynasty", "Bird and Pierce eras", "Deep championship tradition"],
  ),
  1610612739: history(
    "Founded in 1970",
    "The Cavaliers grew from expansion roots into a Northeast Ohio fixture, with eras led by Mark Price, Brad Daugherty, LeBron James, and modern defensive cores.",
    ["2016 NBA champions", "LeBron James era", "Strong guard and big-man lineage"],
  ),
  1610612740: history(
    "New Orleans era since 2002",
    "New Orleans basketball evolved from the Hornets identity into the Pelicans, with star eras around Chris Paul, Anthony Davis, and Zion Williamson.",
    ["Pelicans rebrand", "Chris Paul era", "Athletic modern core"],
  ),
  1610612741: history(
    "Founded in 1966",
    "The Bulls became a global basketball brand through Michael Jordan, Scottie Pippen, Phil Jackson, and two three-peats in the 1990s.",
    ["Six 1990s titles", "Jordan and Pippen dynasty", "United Center culture"],
  ),
  1610612742: history(
    "Founded in 1980",
    "The Mavericks grew from expansion team to modern champion behind Dirk Nowitzki and a tradition of spacing, shot creation, and international stars.",
    ["2011 NBA champions", "Dirk Nowitzki era", "Creative offensive identity"],
  ),
  1610612743: history(
    "ABA roots, NBA since 1976",
    "The Nuggets began as an ABA franchise and built a history around altitude, scoring flair, and playmaking bigs, peaking with the Nikola Jokic era.",
    ["ABA heritage", "2023 NBA champions", "Jokic-led offensive peak"],
  ),
  1610612744: history(
    "Founded in 1946",
    "The Warriors began in Philadelphia, moved west, and became Golden State. From Wilt Chamberlain and Rick Barry to Stephen Curry, the franchise helped define several offensive eras.",
    ["Wilt and Rick Barry eras", "Modern spacing revolution", "Curry-led championship dynasty"],
  ),
  1610612745: history(
    "Founded in 1967",
    "The Rockets moved from San Diego to Houston and built their identity around Hakeem Olajuwon, Yao Ming, and later analytics-forward offenses.",
    ["1994 and 1995 champions", "Hakeem Olajuwon era", "High-volume offensive history"],
  ),
  1610612746: history(
    "Braves to Clippers",
    "The Clippers began as the Buffalo Braves, moved through San Diego, and later remade themselves in Los Angeles through Lob City and star-driven playoff teams.",
    ["Buffalo Braves roots", "Lob City era", "Modern Los Angeles reinvention"],
  ),
  1610612747: history(
    "Minneapolis roots, Los Angeles icon",
    "The Lakers are one of the NBA's signature franchises, with eras spanning Minneapolis, Showtime, Shaq and Kobe, Kobe and Pau, and LeBron-led teams.",
    ["Mikan and Minneapolis titles", "Showtime Lakers", "Kobe and modern championship eras"],
  ),
  1610612748: history(
    "Founded in 1988",
    "The Heat became a model expansion success under Pat Riley's influence, with Alonzo Mourning, Dwyane Wade, the Big Three, and a culture-first identity.",
    ["Wade-led breakthrough", "Big Three championships", "Heat Culture identity"],
  ),
  1610612749: history(
    "Founded in 1968",
    "The Bucks won early with Kareem Abdul-Jabbar and Oscar Robertson, then returned to the top behind Giannis Antetokounmpo.",
    ["1971 NBA champions", "Giannis era", "2021 NBA champions"],
  ),
  1610612750: history(
    "Founded in 1989",
    "The Timberwolves' first sustained identity came through Kevin Garnett, followed by waves of roster reinvention and modern athletic cores.",
    ["Kevin Garnett era", "Target Center fan base", "Modern athletic core"],
  ),
  1610612751: history(
    "ABA roots, Brooklyn since 2012",
    "The Nets began in the ABA, won titles with Julius Erving, spent decades in New Jersey, and moved to Brooklyn with a bold roster-building identity.",
    ["Two ABA championships", "New Jersey Finals runs", "Brooklyn rebrand"],
  ),
  1610612752: history(
    "Original NBA franchise",
    "The Knicks are a charter franchise and Madison Square Garden centerpiece, with title teams led by Willis Reed and Walt Frazier and physical 1990s contenders.",
    ["1970 and 1973 champions", "Madison Square Garden stage", "1990s defensive identity"],
  ),
  1610612753: history(
    "Founded in 1989",
    "The Magic became a fast-rising expansion team behind Shaquille O'Neal and Penny Hardaway, then returned to the Finals with Dwight Howard.",
    ["Shaq and Penny era", "2009 Finals run", "Player-development identity"],
  ),
  1610612754: history(
    "ABA powerhouse",
    "The Pacers won three ABA titles before joining the NBA and are tied to Reggie Miller, disciplined teams, and deep Indiana basketball roots.",
    ["Three ABA titles", "Reggie Miller era", "Indiana basketball culture"],
  ),
  1610612755: history(
    "Syracuse Nationals roots",
    "The 76ers evolved from the Syracuse Nationals into a Philadelphia franchise shaped by Wilt Chamberlain, Julius Erving, Moses Malone, Allen Iverson, and star bigs.",
    ["1967 and 1983 champions", "Dr. J and Moses era", "Iverson era"],
  ),
  1610612756: history(
    "Founded in 1968",
    "The Suns have long been associated with pace, skill, and offensive creativity, from Charles Barkley to Steve Nash and later Finals pushes.",
    ["Barkley Finals era", "Steve Nash MVP years", "Fast-paced identity"],
  ),
  1610612757: history(
    "Founded in 1970",
    "The Trail Blazers won the 1977 title behind Bill Walton and later built memorable eras around Clyde Drexler, Brandon Roy, and Damian Lillard.",
    ["1977 NBA champions", "Clyde Drexler era", "Lillard era"],
  ),
  1610612758: history(
    "Royals to Kings",
    "The Kings trace back to the Rochester Royals, with Sacramento's beloved peak arriving through the early-2000s Chris Webber teams.",
    ["1951 NBA champions", "Sacramento since 1985", "Early-2000s passing offense"],
  ),
  1610612759: history(
    "ABA roots, model dynasty",
    "The Spurs moved from the ABA to become a model NBA organization under Gregg Popovich with Tim Duncan, David Robinson, Tony Parker, and Manu Ginobili.",
    ["Five NBA championships", "Duncan and Popovich era", "Global development model"],
  ),
  1610612760: history(
    "Seattle roots, Oklahoma City since 2008",
    "The Thunder inherited the SuperSonics' NBA lineage and quickly became a contender before retooling around a young modern core.",
    ["Seattle SuperSonics roots", "2012 Finals run", "Draft-driven rebuild"],
  ),
  1610612761: history(
    "Founded in 1995",
    "The Raptors grew from Canada's expansion team into an NBA champion behind Vince Carter's rise, the Lowry-DeRozan era, and the 2019 title run.",
    ["Canada's NBA franchise", "Vince Carter era", "2019 NBA champions"],
  ),
  1610612762: history(
    "New Orleans roots, Utah since 1979",
    "The Jazz moved from New Orleans to Utah and built their identity around Stockton and Malone, Jerry Sloan, and later defensive-development teams.",
    ["Stockton and Malone era", "Jerry Sloan continuity", "Modern rebuild identity"],
  ),
  1610612763: history(
    "Vancouver roots, Memphis since 2001",
    "The Grizzlies began in Vancouver and became Memphis' Grit and Grind franchise behind Zach Randolph, Marc Gasol, Tony Allen, and Mike Conley.",
    ["Moved to Memphis in 2001", "Grit and Grind era", "Physical defensive tradition"],
  ),
  1610612764: history(
    "Chicago Packers roots",
    "The Wizards trace through the Packers, Zephyrs, and Bullets identities, including the 1978 title team and later stars such as Gilbert Arenas and John Wall.",
    ["1978 NBA champions", "Unseld and Hayes era", "Wizards era since 1997"],
  ),
  1610612765: history(
    "Fort Wayne roots",
    "The Pistons moved from Fort Wayne to Detroit and built a blue-collar identity through the Bad Boys and the 2004 defense-first champions.",
    ["Bad Boys titles", "2004 NBA champions", "Defense-first identity"],
  ),
  1610612766: history(
    "Charlotte basketball lineage",
    "The Hornets brand became one of the NBA's recognizable expansion identities, later returning to Charlotte with a teal-and-purple legacy.",
    ["1990s Hornets buzz", "Hornets name restored", "Teal and purple identity"],
  ),
};

const twoWayPlayersByTeam: Record<number, string[]> = {
  1610612737: ["RayJ Dennis", "Keshon Gilbert", "Christian Koloko"],
  1610612738: ["John Tonje"],
  1610612739: ["Tristan Enaruna", "Riley Minix", "Olivier Sarr"],
  1610612740: ["Trey Alexander", "Hunter Dickinson", "Josh Oduro"],
  1610612741: ["Yuki Kawamura", "Mac McClung", "Lachlan Olbrich"],
  1610612742: ["Moussa Cisse", "John Poulakidas", "Tyler Smith"],
  1610612743: ["Curtis Jones", "David Roddy", "K.J. Simpson"],
  1610612744: ["LJ Cryer", "Malevy Leons", "Nate Williams"],
  1610612745: ["Isaiah Crawford", "Tristen Newton"],
  1610612746: ["Norchad Omier", "Sean Pedulla", "TyTy Washington Jr."],
  1610612747: ["Chris Manon", "Drew Timme"],
  1610612748: ["Vladislav Goldin", "Trevor Keels"],
  1610612749: ["Alex Antetokounmpo", "Cormac Ryan"],
  1610612750: ["Enrique Freeman", "Zyon Pullin", "Rocco Zikarsky"],
  1610612751: ["Tyson Etienne", "Chaney Johnson", "E.J. Liddell"],
  1610612752: ["Trey Jemison III", "Dillon Jones", "Kevin McCullar Jr."],
  1610612753: ["Colin Castleton", "Alex Morales"],
  1610612754: ["Taelon Peter", "Jalen Slawson", "Ethan Thompson"],
  1610612755: ["MarJon Beauchamp", "Tyrese Martin"],
  1610612756: ["Koby Brea", "CJ Huntley", "Isaiah Livers"],
  1610612757: ["Jayson Kent", "Caleb Love", "Chris Youngblood"],
  1610612758: ["Patrick Baldwin Jr.", "Daeqwon Plowden", "Isaiah Stevens"],
  1610612759: ["Harrison Ingram", "David Jones Garcia", "Emanuel Miller"],
  1610612760: ["Brooks Barnhizer", "Branden Carlson", "Payton Sandfort"],
  1610612761: ["Chucky Hepburn", "Alijah Martin"],
  1610612762: ["Elijah Harkless", "Blake Hinson", "Oscar Tshiebwe"],
  1610612763: ["Jahmai Mashack", "Rayan Rupert", "Javon Small"],
  1610612764: ["Leaky Black", "Sharife Cooper", "Julian Reese"],
  1610612765: ["Isaac Jones", "Wendell Moore Jr."],
  1610612766: ["Tosan Evbuomwan", "PJ Hall", "Antonio Reeves"],
};

const starPlayerOverrides: Record<number, string> = {
  1610612748: "Bam Adebayo",
  1610612756: "Devin Booker",
  1610612761: "Scottie Barnes",
  1610612763: "Ja Morant",
};

const teamFacts: Record<number, Partial<TeamFacts>> = {
  1610612737: {
    arena: "State Farm Arena",
    founded: "1946",
    location: "Atlanta, Georgia",
    owner: "Tony Ressler",
  },
  1610612738: {
    arena: "TD Garden",
    founded: "1946",
    location: "Boston, Massachusetts",
  },
  1610612739: {
    arena: "Rocket Arena",
    founded: "1970",
    location: "Cleveland, Ohio",
  },
  1610612740: {
    arena: "Smoothie King Center",
    founded: "2002",
    location: "New Orleans, Louisiana",
  },
  1610612741: {
    arena: "United Center",
    founded: "1966",
    location: "Chicago, Illinois",
  },
  1610612742: {
    arena: "American Airlines Center",
    founded: "1980",
    location: "Dallas, Texas",
  },
  1610612743: {
    arena: "Ball Arena",
    founded: "1967",
    location: "Denver, Colorado",
  },
  1610612744: {
    arena: "Chase Center",
    founded: "1946",
    location: "San Francisco, California",
  },
  1610612745: {
    arena: "Toyota Center",
    founded: "1967",
    location: "Houston, Texas",
  },
  1610612746: {
    arena: "Intuit Dome",
    founded: "1970",
    location: "Inglewood, California",
  },
  1610612747: {
    arena: "Crypto.com Arena",
    founded: "1947",
    location: "Los Angeles, California",
  },
  1610612748: {
    arena: "Kaseya Center",
    founded: "1988",
    location: "Miami, Florida",
  },
  1610612749: {
    arena: "Fiserv Forum",
    founded: "1968",
    location: "Milwaukee, Wisconsin",
  },
  1610612750: {
    arena: "Target Center",
    founded: "1989",
    location: "Minneapolis, Minnesota",
  },
  1610612751: {
    arena: "Barclays Center",
    founded: "1967",
    location: "Brooklyn, New York",
  },
  1610612752: {
    arena: "Madison Square Garden",
    founded: "1946",
    location: "New York, New York",
  },
  1610612753: {
    arena: "Kia Center",
    founded: "1989",
    location: "Orlando, Florida",
  },
  1610612754: {
    arena: "Gainbridge Fieldhouse",
    founded: "1967",
    location: "Indianapolis, Indiana",
  },
  1610612755: {
    arena: "Xfinity Mobile Arena",
    founded: "1946",
    location: "Philadelphia, Pennsylvania",
  },
  1610612756: {
    arena: "Footprint Center",
    founded: "1968",
    location: "Phoenix, Arizona",
    nickname: "Suns",
    owner: "Mat Ishbia",
  },
  1610612757: {
    arena: "Moda Center",
    founded: "1970",
    location: "Portland, Oregon",
  },
  1610612758: {
    arena: "Golden 1 Center",
    founded: "1945",
    location: "Sacramento, California",
  },
  1610612759: {
    arena: "Frost Bank Center",
    founded: "1967",
    location: "San Antonio, Texas",
  },
  1610612760: {
    arena: "Paycom Center",
    founded: "1967",
    location: "Oklahoma City, Oklahoma",
  },
  1610612761: {
    arena: "Scotiabank Arena",
    founded: "1995",
    location: "Toronto, Ontario",
  },
  1610612762: {
    arena: "Delta Center",
    founded: "1974",
    location: "Salt Lake City, Utah",
  },
  1610612763: {
    arena: "FedExForum",
    founded: "1995",
    location: "Memphis, Tennessee",
  },
  1610612764: {
    arena: "Capital One Arena",
    founded: "1961",
    location: "Washington, D.C.",
  },
  1610612765: {
    arena: "Little Caesars Arena",
    founded: "1941",
    location: "Detroit, Michigan",
  },
  1610612766: {
    arena: "Spectrum Center",
    founded: "1988",
    location: "Charlotte, North Carolina",
  },
};

export function RostersDashboard() {
  const searchParams = useSearchParams();
  const appliedTeamParamRef = useRef(false);
  const [teams, setTeams] = useState<Team[]>([]);
  const [players, setPlayers] = useState<PlayerListItem[]>([]);
  const [dataStatus, setDataStatus] = useState<DataStatus | undefined>();
  const [selectedTeamId, setSelectedTeamId] = useState<number | null>(null);
  const [summaryMap, setSummaryMap] = useState<Record<number, PlayerSeasonSummary>>({});
  const [detailMap, setDetailMap] = useState<Record<number, PlayerDetail>>({});
  const [mode, setMode] = useState<RosterMode>("teams");
  const [rosterTab, setRosterTab] = useState<RosterTab>("overview");
  const [conferenceFilter, setConferenceFilter] = useState<ConferenceFilter>("all");
  const [teamSearch, setTeamSearch] = useState("");
  const [positionFilter, setPositionFilter] = useState("all");
  const [rosterSearch, setRosterSearch] = useState("");
  const [isInitialLoading, setIsInitialLoading] = useState(true);
  const [isRosterLoading, setIsRosterLoading] = useState(false);
  const [hasInitialError, setHasInitialError] = useState(false);

  useEffect(() => {
    let isActive = true;
    setIsInitialLoading(true);
    setHasInitialError(false);

    Promise.all([getTeams(), getAllPlayers(), getDataStatus()])
      .then(([teamsResponse, allPlayers, statusResponse]) => {
        if (!isActive) {
          return;
        }
        const sortedTeams = [...teamsResponse.teams].sort((left, right) =>
          getTeamName(left).localeCompare(getTeamName(right)),
        );
        setTeams(sortedTeams);
        setPlayers(allPlayers.filter((player) => player.active && player.team));
        setDataStatus(statusResponse);
        setSelectedTeamId(
          sortedTeams.find((team) => team.nba_team_id === defaultSelectedTeamId)?.nba_team_id ??
            sortedTeams[0]?.nba_team_id ??
            null,
        );
      })
      .catch(() => {
        if (isActive) {
          setHasInitialError(true);
        }
      })
      .finally(() => {
        if (isActive) {
          setIsInitialLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (appliedTeamParamRef.current || teams.length === 0) {
      return;
    }
    const requestedTeamId = Number(searchParams?.get("team"));
    const requestedTeam = teams.find((team) => team.nba_team_id === requestedTeamId);
    if (!requestedTeam) {
      return;
    }
    appliedTeamParamRef.current = true;
    setSelectedTeamId(requestedTeam.nba_team_id);
    setRosterTab("overview");
    setMode("roster");
  }, [searchParams, teams]);

  const selectedTeam = useMemo(
    () => teams.find((team) => team.nba_team_id === selectedTeamId) ?? teams[0],
    [selectedTeamId, teams],
  );
  const selectedTheme = getTeamTheme(selectedTeam);
  const selectedRoster = useMemo(
    () =>
      selectedTeam
        ? players.filter((player) => player.team?.nba_team_id === selectedTeam.nba_team_id)
        : [],
    [players, selectedTeam],
  );
  const season = dataStatus?.current_season ?? "2025-26";

  useEffect(() => {
    if (!selectedTeam || selectedRoster.length === 0) {
      setSummaryMap({});
      setDetailMap({});
      return;
    }

    let isActive = true;
    setIsRosterLoading(true);

    Promise.allSettled(
      selectedRoster.map(async (player) => {
        const [summaryResult, detailResult] = await Promise.allSettled([
          getPlayerSummary(player.nba_player_id, season),
          getPlayer(player.nba_player_id),
        ]);
        return {
          detail: detailResult.status === "fulfilled" ? detailResult.value : undefined,
          player,
          summary: summaryResult.status === "fulfilled" ? summaryResult.value : undefined,
        };
      }),
    )
      .then((results) => {
        if (!isActive) {
          return;
        }
        const nextSummaryMap: Record<number, PlayerSeasonSummary> = {};
        const nextDetailMap: Record<number, PlayerDetail> = {};
        results.forEach((result) => {
          if (result.status === "fulfilled") {
            if (result.value.summary) {
              nextSummaryMap[result.value.player.nba_player_id] = result.value.summary;
            }
            if (result.value.detail) {
              nextDetailMap[result.value.player.nba_player_id] = result.value.detail;
            }
          }
        });
        setSummaryMap(nextSummaryMap);
        setDetailMap(nextDetailMap);
      })
      .finally(() => {
        if (isActive) {
          setIsRosterLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [season, selectedRoster, selectedTeam]);

  const rosterRows = useMemo(
    () => buildRosterRows(selectedRoster, summaryMap, detailMap),
    [detailMap, selectedRoster, summaryMap],
  );
  const filteredRosterRows = useMemo(
    () => filterRosterRows(rosterRows, rosterSearch, positionFilter),
    [positionFilter, rosterRows, rosterSearch],
  );
  const visibleTeams = useMemo(
    () => filterTeams(teams, conferenceFilter, teamSearch),
    [conferenceFilter, teamSearch, teams],
  );
  const positionOptions = useMemo(() => getPositionOptions(rosterRows), [rosterRows]);
  const selectedSnapshot = useMemo(
    () => getTeamSnapshot(selectedTeam, selectedRoster, summaryMap, detailMap),
    [detailMap, selectedRoster, selectedTeam, summaryMap],
  );
  const selectedHistory = selectedTeam ? teamHistories[selectedTeam.nba_team_id] : undefined;
  const selectedStarPlayer = useMemo(
    () => getStarPlayer(selectedRoster, summaryMap, selectedTeam?.nba_team_id),
    [selectedRoster, selectedTeam, summaryMap],
  );
  return (
    <AppShell
      active="Teams"
      showTopSearch
      themeStyle={getTeamThemeStyle(selectedTheme)}
      variant="topbar"
    >
      <div className="rosters-experience" style={getTeamThemeStyle(selectedTheme)}>
        {mode === "teams" ? (
          <RostersHomeView
            conferenceFilter={conferenceFilter}
            hasInitialError={hasInitialError}
            isInitialLoading={isInitialLoading}
            onConferenceFilterChange={setConferenceFilter}
            onOpenRoster={(team) => {
              setSelectedTeamId(team.nba_team_id);
              setRosterTab("overview");
              setMode("roster");
            }}
            onSearchChange={setTeamSearch}
            search={teamSearch}
            teams={visibleTeams}
          />
        ) : (
          <RosterDetailView
            filteredRosterRows={filteredRosterRows}
            isRosterLoading={isRosterLoading}
            onBack={() => setMode("teams")}
            onPositionFilterChange={setPositionFilter}
            onRosterTabChange={setRosterTab}
            onRosterSearchChange={setRosterSearch}
            positionFilter={positionFilter}
            positionOptions={positionOptions}
            rosterRows={rosterRows}
            rosterSearch={rosterSearch}
            rosterTab={rosterTab}
            season={season}
            selectedHistory={selectedHistory}
            selectedSnapshot={selectedSnapshot}
            selectedStarPlayer={selectedStarPlayer}
            selectedTeam={selectedTeam}
          />
        )}
      </div>
    </AppShell>
  );
}

function RostersHomeView({
  conferenceFilter,
  hasInitialError,
  isInitialLoading,
  onConferenceFilterChange,
  onOpenRoster,
  onSearchChange,
  search,
  teams,
}: {
  conferenceFilter: ConferenceFilter;
  hasInitialError: boolean;
  isInitialLoading: boolean;
  onConferenceFilterChange: (filter: ConferenceFilter) => void;
  onOpenRoster: (team: Team) => void;
  onSearchChange: (value: string) => void;
  search: string;
  teams: Team[];
}) {
  return (
    <div className="rosters-home-layout">
      <section className="rosters-home-main">
        <div className="rosters-home-heading">
          <div className="rosters-home-heading-text">
            <h1>NBA Team Rosters</h1>
            <p>Browse every team, explore roster depth, team history, and player details.</p>
          </div>
          <a className="rosters-standings-link" href="/standings">
            <span className="rosters-standings-icon" aria-hidden="true" />
            <span>
              <strong>League Standings</strong>
              <em>Full conference &amp; division tables</em>
            </span>
            <span className="rosters-standings-arrow" aria-hidden="true">
              →
            </span>
          </a>
        </div>

        <div className="rosters-filter-row primary" aria-label="Conference filters">
          <button
            className={conferenceFilter === "all" ? "active" : ""}
            onClick={() => onConferenceFilterChange("all")}
            type="button"
          >
            All Teams
          </button>
          <button
            className={conferenceFilter === "East" ? "active" : ""}
            onClick={() => onConferenceFilterChange("East")}
            type="button"
          >
            Eastern Conference
          </button>
          <button
            className={conferenceFilter === "West" ? "active" : ""}
            onClick={() => onConferenceFilterChange("West")}
            type="button"
          >
            Western Conference
          </button>
        </div>

        <div className="rosters-filter-row controls">
          <label>
            <span className="sr-only">Search teams</span>
            <input
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search teams..."
              value={search}
            />
          </label>
        </div>

        {isInitialLoading ? (
          <div className="rosters-empty">Loading teams...</div>
        ) : hasInitialError ? (
          <div className="rosters-empty">Team data is unavailable right now.</div>
        ) : (
          <div className="team-card-grid" aria-label="NBA teams">
            {teams.map((team) => (
              <TeamCard key={team.nba_team_id} onSelect={() => onOpenRoster(team)} team={team} />
            ))}
          </div>
        )}
        <p className="rosters-showing-line">Showing all {teams.length || 30} teams</p>
      </section>
    </div>
  );
}

function TeamCard({ onSelect, team }: { onSelect: () => void; team: Team }) {
  const meta = getTeamMeta(team);

  return (
    <button
      aria-label={`${team.abbreviation} ${getTeamName(team)}`}
      className="team-roster-card"
      onClick={onSelect}
      style={getTeamThemeStyle(getTeamTheme(team))}
      type="button"
    >
      <span className="team-card-logo" aria-hidden="true">
        <TeamLogoMark team={team} />
      </span>
      <span className="team-card-name">
        <strong>{team.city}</strong>
        <strong>{team.name}</strong>
      </span>
      <em>
        {meta.conference} / {meta.division}
      </em>
    </button>
  );
}

export function TeamLogoMark({
  label,
  team,
  variant = "standard",
}: {
  label?: string;
  team: Team;
  variant?: "hero" | "standard";
}) {
  const displayLabel = label ?? team.abbreviation;
  const motif = getTeamLogoMotif(team);

  return (
    <svg
      aria-hidden="true"
      className={`team-logo-mark team-logo-${variant} team-logo-${motif} team-letter-logo`}
      viewBox="0 0 120 120"
    >
      <circle className="team-logo-ring" cx="60" cy="60" r="56" />
      <circle className="team-logo-core" cx="60" cy="60" r="44" />
      <g className="team-logo-hidden-motif">
        <TeamLogoMotifShape motif={motif} />
      </g>
      <text className="team-logo-label" dominantBaseline="middle" textAnchor="middle" x="60" y="66">
        {displayLabel}
      </text>
    </svg>
  );
}

function TeamTextMark({ label }: { label: string }) {
  return (
    <svg aria-hidden="true" className="team-text-mark" viewBox="0 0 100 100">
      <text
        className="team-text-mark-label"
        dominantBaseline="middle"
        textAnchor="middle"
        x="50"
        y="55"
      >
        {label}
      </text>
    </svg>
  );
}

function TeamLogoMotifShape({ motif }: { motif: TeamLogoMotif }) {
  switch (motif) {
    case "antler":
      return (
        <g className="team-logo-motif">
          <path d="M43 82V48c0-15 13-21 17-30 4 9 17 15 17 30v34" />
          <path d="M43 50 27 36M43 60 26 60M77 50l16-14M77 60h17M52 38l-9-18M68 38l9-18" />
        </g>
      );
    case "bear":
      return (
        <g className="team-logo-motif filled">
          <circle cx="60" cy="66" r="18" />
          <circle cx="39" cy="39" r="7" />
          <circle cx="53" cy="32" r="7" />
          <circle cx="69" cy="32" r="7" />
          <circle cx="83" cy="39" r="7" />
          <path d="M47 68c8 8 18 8 26 0" />
        </g>
      );
    case "bridge":
      return (
        <g className="team-logo-motif">
          <path d="M30 82V40M90 82V40M22 82h76" />
          <path d="M30 40c15 22 45 22 60 0M40 82V54M50 82V59M60 82V62M70 82V59M80 82V54" />
        </g>
      );
    case "bull":
      return (
        <g className="team-logo-motif">
          <path d="M29 43c14-12 23-3 31 12 8-15 17-24 31-12-8 5-12 14-10 26-6 14-36 14-42 0 2-12-2-21-10-26Z" />
          <path d="M49 62h.5M70 62h.5M51 78c6 4 12 4 18 0" />
        </g>
      );
    case "claw":
      return (
        <g className="team-logo-motif">
          <path d="M37 28c-2 22 3 43 16 62M60 24c-6 21-4 43 6 67M84 30c-12 18-18 39-16 62" />
        </g>
      );
    case "compass":
      return (
        <g className="team-logo-motif">
          <circle cx="60" cy="60" r="30" />
          <path d="m60 20 10 40-10 40-10-40 10-40ZM20 60l40-10 40 10-40 10-40-10Z" />
        </g>
      );
    case "crown":
      return (
        <g className="team-logo-motif">
          <path d="M28 78h64l-8-39-17 19-7-29-7 29-17-19-8 39Z" />
          <path d="M31 86h58" />
        </g>
      );
    case "flame":
      return (
        <g className="team-logo-motif filled">
          <path d="M62 91c20-11 24-31 12-47-3 12-8 17-15 22 4-18-4-32-15-43 1 20-17 28-17 46 0 18 16 29 35 22Z" />
        </g>
      );
    case "gear":
      return (
        <g className="team-logo-motif">
          <path d="M60 25v13M60 82v13M25 60h13M82 60h13M35 35l9 9M76 76l9 9M85 35l-9 9M44 76l-9 9" />
          <circle cx="60" cy="60" r="25" />
          <circle cx="60" cy="60" r="10" />
        </g>
      );
    case "hawk":
      return (
        <g className="team-logo-hawk-mark">
          <path
            className="hawk-red-sweep"
            d="M24 73c7-31 31-50 68-49-26 8-43 23-53 45 13-14 28-22 49-24-20 12-35 27-46 49-10-3-16-10-18-21Z"
          />
          <path
            className="hawk-feather hawk-feather-main"
            d="M25 72c20-27 41-40 70-42-19 8-34 20-44 35 13-10 28-16 43-17-19 9-34 22-46 40-11-1-19-6-23-16Z"
          />
          <path
            className="hawk-feather hawk-feather-upper"
            d="M38 62c17-15 33-24 55-27-18 8-31 18-42 31"
          />
          <path
            className="hawk-feather hawk-feather-mid"
            d="M34 72c18-12 36-19 58-21-18 8-32 18-44 32"
          />
          <path
            className="hawk-feather hawk-feather-low"
            d="M41 86c11-9 24-15 39-18-12 8-23 16-31 25"
          />
          <path className="hawk-beak" d="M91 31c-8 1-15 4-22 9 11-1 19-4 26-9Z" />
        </g>
      );
    case "hornet":
      return (
        <g className="team-logo-motif filled">
          <path d="M60 31c14 8 22 21 22 38L60 89 38 69c0-17 8-30 22-38Z" />
          <path d="M41 48 24 38M79 48l17-10M38 63H22M82 63h16M49 52h22M47 66h26" />
          <path d="M44 35c-12-4-22 0-31 10 14 0 25 5 32 15M76 35c12-4 22 0 31 10-14 0-25 5-32 15" />
        </g>
      );
    case "horse":
      return (
        <g className="team-logo-motif filled">
          <path d="M35 85c0-29 7-49 30-61 17 5 24 16 22 33-8-7-17-10-27-8 8 8 8 18 1 27 9 1 16 5 21 12H35Z" />
        </g>
      );
    case "liberty":
      return (
        <g className="team-logo-motif">
          <path d="M60 24v72M42 42h36M49 32l11-14 11 14M45 96h30" />
          <path d="M39 54c14 5 28 5 42 0" />
        </g>
      );
    case "lightning":
      return (
        <g className="team-logo-motif filled">
          <path d="M68 18 31 65h24l-7 37 40-51H62l6-33Z" />
        </g>
      );
    case "monument":
      return (
        <g className="team-logo-motif">
          <path d="M60 18 45 92h30L60 18Z" />
          <path d="M36 92h48M31 101h58M51 55h18" />
          <path d="M60 9 64 18 74 19 66 25l2 10-8-5-8 5 2-10-8-6 10-1 4-9ZM25 88c9-23 20-38 35-46 15 8 26 23 35 46" />
        </g>
      );
    case "mountain":
      return (
        <g className="team-logo-motif">
          <path d="M22 84 48 35l16 27 11-17 24 39H22Z" />
          <path d="m48 35 2 25 14 2M75 45l-3 19 11 3" />
        </g>
      );
    case "net":
      return (
        <g className="team-logo-motif">
          <circle cx="60" cy="60" r="31" />
          <path d="M30 60h60M60 29v62M39 39c13 9 29 9 42 0M39 81c13-9 29-9 42 0" />
        </g>
      );
    case "note":
      return (
        <g className="team-logo-motif">
          <path d="M49 28v45c0 9-7 16-17 16s-16-5-16-12 7-12 17-12c4 0 8 1 11 3V28h43v14H49" />
          <path d="M87 42v32M60 58h4M69 52h4M78 46h4M60 72h4M69 67h4M78 61h4" />
        </g>
      );
    case "pelican":
      return (
        <g className="team-logo-motif filled">
          <path d="M60 23c-20 11-33 25-39 46 16-9 28-8 39 8 11-16 23-17 39-8-6-21-19-35-39-46Z" />
          <path d="M47 67c8 9 18 9 26 0" />
        </g>
      );
    case "rocket":
      return (
        <g className="team-logo-motif">
          <path d="M60 20c16 12 23 28 18 49L60 94 42 69c-5-21 2-37 18-49Z" />
          <path d="M48 78 34 91M72 78l14 13M51 49h18" />
        </g>
      );
    case "shamrock":
      return (
        <g className="team-logo-motif filled">
          <circle cx="48" cy="50" r="14" />
          <circle cx="72" cy="50" r="14" />
          <circle cx="60" cy="31" r="14" />
          <path d="M60 60c-1 15-7 24-20 32 13-2 25-6 32-17 4-6 6-12 7-20Z" />
        </g>
      );
    case "skyline":
      return (
        <g className="team-logo-motif">
          <path d="M24 84h72M31 84V58h11v26M49 84V38h15v46M71 84V51h18v33" />
          <path d="M49 38 57 25l7 13" />
        </g>
      );
    case "speed":
      return (
        <g className="team-logo-motif">
          <path d="M25 45h46M18 60h70M31 75h42" />
          <path d="M72 32c17 13 21 38 5 55" />
        </g>
      );
    case "spur":
      return (
        <g className="team-logo-motif">
          <path d="M60 22v76M28 60h64" />
          <path d="m60 22 9 26 27 12-27 12-9 26-9-26-27-12 27-12 9-26Z" />
        </g>
      );
    case "star":
      return (
        <g className="team-logo-motif filled">
          <path d="m60 22 10 26 28 2-21 18 7 28-24-15-24 15 7-28-21-18 28-2 10-26Z" />
        </g>
      );
    case "sun":
      return (
        <g className="team-logo-motif">
          <circle cx="60" cy="60" r="21" />
          <path d="M60 17v18M60 85v18M17 60h18M85 60h18M30 30l13 13M77 77l13 13M90 30 77 43M43 77 30 90" />
        </g>
      );
    case "sunset":
      return (
        <g className="team-logo-motif">
          <path d="M22 76h76M31 76c2-22 15-36 29-36s27 14 29 36" />
          <path d="M29 87h62M39 98h42" />
        </g>
      );
    case "sword":
      return (
        <g className="team-logo-motif">
          <path d="M79 20 47 68l-14 19 19-14 48-32-21-21Z" />
          <path d="M41 72 28 85M35 59l26 26" />
        </g>
      );
    case "trail":
      return (
        <g className="team-logo-motif">
          <path d="M36 68c14-21 30-26 48-17M36 80c15-15 31-18 48-10M36 57c15-26 30-34 48-27" />
        </g>
      );
    case "wolf":
      return (
        <g className="team-logo-motif">
          <circle cx="73" cy="34" r="12" />
          <path d="M24 88c18-28 35-42 52-43 9 0 16 4 22 12" />
          <path d="M31 82c13-17 26-25 39-25 9 0 17 4 23 12M39 94c12-12 24-18 36-18 7 0 14 2 21 7" />
          <path d="M31 61 46 40l11 15 10-10" />
        </g>
      );
    default:
      return null;
  }
}

function TeamOverviewPanel({
  history,
  rosterRows,
  snapshot,
  starPlayer,
  team,
}: {
  history: TeamHistory | undefined;
  rosterRows: RosterPlayer[];
  snapshot: TeamSnapshot;
  starPlayer: StarPlayer | undefined;
  team: Team | undefined;
}) {
  const teamLeaders = useMemo(
    () => ({
      points: topByStat(rosterRows, "points_per_game", 3),
      assists: topByStat(rosterRows, "assists_per_game", 3),
      rebounds: topByStat(rosterRows, "rebounds_per_game", 3),
    }),
    [rosterRows],
  );
  const rosterComposition = useMemo(() => {
    const counts = new Map<string, number>();
    rosterRows.forEach((row) => {
      const group = getPositionGroup(row.player.position);
      counts.set(group, (counts.get(group) ?? 0) + 1);
    });
    return positionOrder
      .filter((group) => group !== "Unlisted")
      .map((group) => ({ group, count: counts.get(group) ?? 0 }))
      .filter((entry) => entry.count > 0);
  }, [rosterRows]);

  if (!team) {
    return <div className="rosters-empty">Select a team to view its overview.</div>;
  }

  const meta = getTeamMeta(team);
  const facts = getTeamFacts(team);
  const headCoach = getHeadCoach(team);

  return (
    <div className="team-dashboard-overview">
      <div className="team-dashboard-kpis">
        <TeamMetricCard
          detail="Best finish and title history"
          label="NBA Championships"
          value={getChampionshipSummary(team)}
          variant="trophy"
        />
        <TeamMetricCard
          detail="Average active-roster age"
          label="Avg Age"
          value={formatNumber(snapshot.avgAge)}
          variant="people"
        />
        <TeamMetricCard
          detail="Per-game team rotation load"
          label="Avg Minutes"
          value={formatNumber(snapshot.avgMpg)}
          variant="clock"
        />
        <TeamMetricCard
          detail={`${meta.conference}ern Conference`}
          label="Conference / Division"
          value={`${meta.conference} / ${meta.division}`}
          variant="conference"
        />
      </div>

      <div className="team-dashboard-grid">
        <div className="team-dashboard-main">
          <section className="team-dashboard-card team-dashboard-about">
            <div>
              <span className="team-dashboard-eyebrow">Team History</span>
              <h2>About the {team.name}</h2>
              {history ? (
                <>
                  <p className="team-overview-copy">{history.overview}</p>
                  <ul className="team-overview-highlights">
                    {history.highlights.map((highlight) => (
                      <li key={highlight}>{highlight}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="team-overview-copy">Team history is not available yet.</p>
              )}
            </div>

            <TeamCompositionDonut
              composition={rosterComposition}
              rosterCount={snapshot.rosterCount}
              theme={getTeamTheme(team)}
            />
          </section>

          <section className="team-dashboard-card team-overview-leaders">
            <div className="team-dashboard-card-heading">
              <h2>Team Leaders</h2>
              <span>{team.abbreviation} per-game leaders</span>
            </div>
            <div className="team-overview-leaders-grid">
              <TeamLeaderColumn
                format={(row) => formatNumber(row.summary?.points_per_game)}
                label="Points (PPG)"
                rows={teamLeaders.points}
              />
              <TeamLeaderColumn
                format={(row) => formatNumber(row.summary?.assists_per_game)}
                label="Assists (APG)"
                rows={teamLeaders.assists}
              />
              <TeamLeaderColumn
                format={(row) => formatNumber(row.summary?.rebounds_per_game)}
                label="Rebounds (RPG)"
                rows={teamLeaders.rebounds}
              />
            </div>
          </section>
        </div>

        <aside className="team-dashboard-side">
          <TeamLeadershipCard
            facts={facts}
            headCoach={headCoach}
            starPlayer={starPlayer}
            team={team}
          />
        </aside>
      </div>
    </div>
  );
}

function TeamMetricCard({
  detail,
  label,
  value,
  variant,
}: {
  detail: string;
  label: string;
  value: string;
  variant: "clock" | "conference" | "people" | "trophy";
}) {
  const symbol = {
    clock: "MIN",
    conference: "DIV",
    people: "AGE",
    trophy: "RING",
  }[variant];

  return (
    <section className={`team-dashboard-metric team-dashboard-metric-${variant}`}>
      <span aria-hidden="true">{symbol}</span>
      <strong>{value}</strong>
      <em>{label}</em>
      <p>{detail}</p>
    </section>
  );
}

function TeamCompositionDonut({
  composition,
  rosterCount,
  theme,
}: {
  composition: { count: number; group: string }[];
  rosterCount: number;
  theme: ReturnType<typeof getTeamTheme>;
}) {
  const background = getCompositionGradient(composition, theme);

  return (
    <div className="team-composition-card">
      <h3>Roster Composition</h3>
      {composition.length > 0 ? (
        <div className="team-composition-body">
          <div
            className="team-composition-donut"
            style={{ "--composition-chart": background } as CSSProperties}
          >
            <strong>{rosterCount}</strong>
          </div>
          <ul className="team-overview-composition">
            {composition.map((entry, index) => (
              <li
                key={entry.group}
                style={
                  { "--composition-color": getCompositionColor(index, theme) } as CSSProperties
                }
              >
                <i aria-hidden="true" />
                <strong>{entry.count}</strong>
                {entry.group}
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="team-overview-copy">Roster data is not available yet.</p>
      )}
    </div>
  );
}

function TeamLeaderColumn({
  format,
  label,
  rows,
}: {
  format: (row: RosterPlayer) => string;
  label: string;
  rows: RosterPlayer[];
}) {
  const maxValue = Math.max(
    ...rows.map((row) => Number.parseFloat(format(row))).filter((value) => Number.isFinite(value)),
    1,
  );

  return (
    <div className="team-overview-leaders-column">
      <h3>{label}</h3>
      {rows.length > 0 ? (
        <ol>
          {rows.map((row, index) => {
            const value = Number.parseFloat(format(row));
            const width = Number.isFinite(value) ? Math.max(8, (value / maxValue) * 100) : 8;
            return (
              <li key={row.player.id}>
                <span>
                  <em>{index + 1}</em>
                  {row.player.full_name}
                </span>
                <i aria-hidden="true">
                  <b style={{ width: `${width}%` }} />
                </i>
                <strong>{format(row)}</strong>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="team-overview-copy">Season stats are not available yet.</p>
      )}
    </div>
  );
}

function TeamLeadershipCard({
  facts,
  headCoach,
  starPlayer,
  team,
}: {
  facts: TeamFacts;
  headCoach: string;
  starPlayer: StarPlayer | undefined;
  team: Team;
}) {
  return (
    <section className="team-dashboard-card team-leadership-card">
      <h2>Team Leadership</h2>
      <div className="team-leader-profile">
        <span className="team-dashboard-eyebrow">Head Coach</span>
        <div className="team-staff-avatar" aria-hidden="true">
          <TeamTextMark label="HC" />
        </div>
        <div>
          <strong>{headCoach}</strong>
          <span>{team.name}</span>
        </div>
      </div>

      <div className="team-leader-profile">
        <span className="team-dashboard-eyebrow">Owner</span>
        <div className="team-owner-logo" aria-hidden="true">
          <TeamLogoMark team={team} />
        </div>
        <div>
          <strong>{facts.owner}</strong>
          <span>Principal owner / ownership group</span>
        </div>
      </div>

      {starPlayer ? (
        <div className="team-leader-profile">
          <span className="team-dashboard-eyebrow">Star Player</span>
          <div className="team-star-number" aria-hidden="true">
            <PlayerNumberMark player={starPlayer.player} />
          </div>
          <div>
            <strong>{starPlayer.player.full_name}</strong>
            <span>{formatNumber(starPlayer.summary?.points_per_game)} PPG</span>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function RosterDetailView({
  filteredRosterRows,
  isRosterLoading,
  onBack,
  onPositionFilterChange,
  onRosterTabChange,
  onRosterSearchChange,
  positionFilter,
  positionOptions,
  rosterRows,
  rosterSearch,
  rosterTab,
  season,
  selectedHistory,
  selectedSnapshot,
  selectedStarPlayer,
  selectedTeam,
}: {
  filteredRosterRows: RosterPlayer[];
  isRosterLoading: boolean;
  onBack: () => void;
  onPositionFilterChange: (value: string) => void;
  onRosterTabChange: (tab: RosterTab) => void;
  onRosterSearchChange: (value: string) => void;
  positionFilter: string;
  positionOptions: string[];
  rosterRows: RosterPlayer[];
  rosterSearch: string;
  rosterTab: RosterTab;
  season: string;
  selectedHistory: TeamHistory | undefined;
  selectedSnapshot: TeamSnapshot;
  selectedStarPlayer: StarPlayer | undefined;
  selectedTeam: Team | undefined;
}) {
  const [hoveredPlayerId, setHoveredPlayerId] = useState<number | null>(null);
  const [hoverPosition, setHoverPosition] = useState<{ top: number; left: number } | null>(null);
  const rowShowTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const rowHideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      clearHoverTimer(rowShowTimer);
      clearHoverTimer(rowHideTimer);
    },
    [],
  );

  const hoveredRow = hoveredPlayerId
    ? filteredRosterRows.find((row) => row.player.nba_player_id === hoveredPlayerId)
    : undefined;

  function previewPlayerRow(playerId: number, target: HTMLElement) {
    clearHoverTimer(rowShowTimer);
    clearHoverTimer(rowHideTimer);
    const rect = target.getBoundingClientRect();
    rowShowTimer.current = setTimeout(() => {
      setHoveredPlayerId(playerId);
      setHoverPosition({
        top: Math.max(12, Math.min(rect.top, window.innerHeight - 560)),
        left: Math.max(12, Math.min(rect.right + 14, window.innerWidth - 416)),
      });
    }, 300);
  }

  function hidePlayerRowPreview() {
    clearHoverTimer(rowShowTimer);
    clearHoverTimer(rowHideTimer);
    rowHideTimer.current = setTimeout(() => {
      setHoveredPlayerId(null);
    }, 140);
  }

  function keepPlayerRowPreviewOpen() {
    clearHoverTimer(rowHideTimer);
  }

  if (!selectedTeam) {
    return <div className="rosters-empty">Select a team to view its roster.</div>;
  }

  const selectedFacts = getTeamFacts(selectedTeam);

  return (
    <div className="roster-detail-layout">
      <section className="team-detail-hero">
        <div className="team-detail-back-row">
          <button className="roster-back-button" onClick={onBack} type="button">
            Back to Teams
          </button>
        </div>
        <div className="team-detail-brand">
          <TeamLogoMark team={selectedTeam} variant="hero" />
          <div className="roster-team-title">
            <p className="team-detail-kicker">
              {selectedFacts.location} <span>Founded in {selectedFacts.founded}</span>
            </p>
            <h1>
              {getTeamName(selectedTeam)}
              <span aria-hidden="true">{selectedTeam.abbreviation}</span>
            </h1>
            <p>{season} Season</p>
          </div>
        </div>
        <div className="team-detail-ambient" aria-hidden="true">
          <TeamLogoMark team={selectedTeam} variant="hero" />
        </div>
        <div className="roster-header-metrics">
          <span>
            <strong>{selectedSnapshot.rosterCount}</strong>
            Players
          </span>
          <span>
            <strong>${selectedSnapshot.payroll.toFixed(1)}M</strong>
            Total Payroll
          </span>
          <span>
            <strong>${selectedSnapshot.capSpace.toFixed(1)}M</strong>
            Cap Space
          </span>
          <span
            className="cap-ring"
            style={{ "--cap-used": `${selectedSnapshot.capUsed}%` } as CSSProperties}
          >
            <strong>{selectedSnapshot.capUsed}%</strong>
            Cap Used
          </span>
        </div>
      </section>

      <section className="roster-workspace panel">
        <div className="roster-tabs">
          <button
            className={rosterTab === "overview" ? "active" : ""}
            onClick={() => onRosterTabChange("overview")}
            type="button"
          >
            Overview
          </button>
          <button
            className={rosterTab === "players" ? "active" : ""}
            onClick={() => onRosterTabChange("players")}
            type="button"
          >
            Roster
          </button>
        </div>

        {rosterTab === "overview" ? (
          <TeamOverviewPanel
            history={selectedHistory}
            rosterRows={rosterRows}
            snapshot={selectedSnapshot}
            starPlayer={selectedStarPlayer}
            team={selectedTeam}
          />
        ) : rosterTab === "players" ? (
          <>
            <div className="roster-control-row">
              <select
                aria-label="Position filter"
                onChange={(event) => onPositionFilterChange(event.target.value)}
                value={positionFilter}
              >
                <option value="all">Position</option>
                {positionOptions.map((position) => (
                  <option key={position} value={position}>
                    {position}
                  </option>
                ))}
              </select>
              <label>
                <span className="sr-only">Search roster</span>
                <input
                  onChange={(event) => onRosterSearchChange(event.target.value)}
                  placeholder="Search roster..."
                  value={rosterSearch}
                />
              </label>
            </div>

            <div className="roster-content-grid">
              <div className="roster-table-wrap">
                <table className="roster-table" aria-label={`${getTeamName(selectedTeam)} roster`}>
                  <thead>
                    <tr>
                      <th>Player</th>
                      <th>Pos</th>
                      <th>Age</th>
                      <th>Height</th>
                      <th>Weight</th>
                      <th>GP</th>
                      <th>MPG</th>
                      <th>PPG</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRosterRows.map((row) => (
                      <tr
                        key={row.player.id}
                        onMouseEnter={(event) =>
                          previewPlayerRow(row.player.nba_player_id, event.currentTarget)
                        }
                        onMouseLeave={hidePlayerRowPreview}
                      >
                        <td>
                          <span className="roster-player-cell">
                            <span className="roster-player-avatar" aria-hidden="true">
                              <PlayerNumberMark player={row.player} />
                            </span>
                            <a href={`/players/${row.player.nba_player_id}`}>
                              <strong>{row.player.full_name}</strong>
                            </a>
                          </span>
                        </td>
                        <td>{getPositionAbbreviation(row.player.position)}</td>
                        <td>{formatAge(row.detail?.birthdate)}</td>
                        <td>{row.detail?.height ?? "--"}</td>
                        <td>{formatWeight(row.detail?.weight_pounds)}</td>
                        <td>{row.summary?.games_played ?? "--"}</td>
                        <td>{formatNumber(row.summary?.minutes_per_game)}</td>
                        <td>{formatNumber(row.summary?.points_per_game)}</td>
                        <td>
                          <span
                            className={row.isTwoWay ? "status-pill two-way" : "status-pill active"}
                          >
                            {row.isTwoWay ? "Two-Way" : "Active"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="roster-table-caption">
                  {isRosterLoading
                    ? "Loading season summaries..."
                    : `Showing ${filteredRosterRows.length} of ${rosterRows.length} players`}
                </p>
              </div>
            </div>
            {hoveredRow && hoverPosition ? (
              <PlayerHoverDetailPanel
                onMouseEnter={keepPlayerRowPreviewOpen}
                onMouseLeave={hidePlayerRowPreview}
                position={hoverPosition}
                row={hoveredRow}
                team={selectedTeam}
              />
            ) : null}
          </>
        ) : null}
      </section>
    </div>
  );
}

function PlayerHoverDetailPanel({
  onMouseEnter,
  onMouseLeave,
  position,
  row,
  team,
}: {
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  position: { top: number; left: number };
  row: RosterPlayer;
  team: Team;
}) {
  const summary = row.summary;
  const shooting = scoreFromPercent(summary?.true_shooting_percentage, 0.48, 0.68);
  const playmaking = scoreFromValue(summary?.assists_per_game, 1, 9);
  const scoring = scoreFromValue(summary?.points_per_game, 4, 30);
  const activity = scoreFromValue(summary?.minutes_per_game, 8, 36);

  return (
    <aside
      className="player-hover-panel"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{ top: position.top, left: position.left }}
    >
      <div className="roster-player-card">
        <div className="roster-card-hero">
          <div className="roster-player-headshot">
            <PlayerNumberMark player={row.player} />
          </div>
          <div>
            <h2>{row.player.full_name}</h2>
            <p>{row.player.position ?? "Position TBD"}</p>
            <p>
              {row.detail?.height ?? "--"} / {formatWeight(row.detail?.weight_pounds)} / Age{" "}
              {formatAge(row.detail?.birthdate)}
            </p>
            <span className="roster-card-badges">
              <span className={row.isTwoWay ? "roster-active-dot two-way" : "roster-active-dot"}>
                {row.isTwoWay ? "Two-Way" : "Active"}
              </span>
            </span>
          </div>
        </div>

        <div className="attribute-block">
          <h3>Attributes</h3>
          <AttributeBar label="Shooting" value={shooting} />
          <AttributeBar label="Playmaking" value={playmaking} />
          <AttributeBar label="Scoring" value={scoring} />
          <AttributeBar label="Activity" value={activity} />
        </div>

        <div className="contract-block">
          <h3>Roster Context</h3>
          <dl>
            <div>
              <dt>Team</dt>
              <dd>{getTeamName(team)}</dd>
            </div>
            <div>
              <dt>Depth Proxy</dt>
              <dd>{formatNumber(summary?.minutes_per_game)} MPG</dd>
            </div>
            <div>
              <dt>Games Played</dt>
              <dd>{summary?.games_played ?? "--"}</dd>
            </div>
          </dl>
        </div>
      </div>
    </aside>
  );
}

function AttributeBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="attribute-row">
      <span>{label}</span>
      <i>
        <b style={{ width: `${value}%` }} />
      </i>
      <strong>{value}</strong>
    </div>
  );
}

function buildRosterRows(
  roster: PlayerListItem[],
  summaries: Record<number, PlayerSeasonSummary>,
  details: Record<number, PlayerDetail>,
): RosterPlayer[] {
  const rows = roster.map((player) => ({
    detail: details[player.nba_player_id],
    isTwoWay: isTwoWayPlayer(player),
    player,
    summary: summaries[player.nba_player_id],
  }));

  return rows.sort(compareRosterPlayers);
}

function filterRosterRows(
  rows: RosterPlayer[],
  search: string,
  positionFilter: string,
): RosterPlayer[] {
  const normalizedSearch = search.trim().toLowerCase();
  return rows.filter((row) => {
    const matchesPosition =
      positionFilter === "all" || getPositionGroup(row.player.position) === positionFilter;
    const matchesSearch =
      normalizedSearch.length === 0 ||
      row.player.full_name.toLowerCase().includes(normalizedSearch) ||
      (row.player.position ?? "").toLowerCase().includes(normalizedSearch);
    return matchesPosition && matchesSearch;
  });
}

function getPositionOptions(rows: RosterPlayer[]): string[] {
  return positionOrder.filter((position) =>
    rows.some((row) => getPositionGroup(row.player.position) === position),
  );
}

function filterTeams(teams: Team[], conferenceFilter: ConferenceFilter, search: string): Team[] {
  const normalizedSearch = search.trim().toLowerCase();
  return teams.filter((team) => {
    const meta = getTeamMeta(team);
    const matchesConference = conferenceFilter === "all" || meta.conference === conferenceFilter;
    const matchesSearch =
      normalizedSearch.length === 0 ||
      getTeamName(team).toLowerCase().includes(normalizedSearch) ||
      team.abbreviation.toLowerCase().includes(normalizedSearch);
    return matchesConference && matchesSearch;
  });
}

function compareRosterPlayers(left: RosterPlayer, right: RosterPlayer): number {
  if (left.isTwoWay !== right.isTwoWay) {
    return left.isTwoWay ? 1 : -1;
  }

  const leftPosition = positionOrder.indexOf(getPositionGroup(left.player.position));
  const rightPosition = positionOrder.indexOf(getPositionGroup(right.player.position));
  if (leftPosition !== rightPosition) {
    return leftPosition - rightPosition;
  }

  const leftMinutes = left.summary?.minutes_per_game ?? -1;
  const rightMinutes = right.summary?.minutes_per_game ?? -1;
  if (rightMinutes !== leftMinutes) {
    return rightMinutes - leftMinutes;
  }

  return left.player.full_name.localeCompare(right.player.full_name);
}

function getTeamSnapshot(
  team: Team | undefined,
  roster: PlayerListItem[],
  summaries: Record<number, PlayerSeasonSummary> = {},
  details: Record<number, PlayerDetail> = {},
): TeamSnapshot {
  const minutes = roster
    .map((player) => summaries[player.nba_player_id]?.minutes_per_game)
    .filter((value): value is number => typeof value === "number");
  const ages = roster
    .map((player) => calculateAge(details[player.nba_player_id]?.birthdate))
    .filter((value): value is number => typeof value === "number");
  const avgMpg =
    minutes.length > 0 ? minutes.reduce((total, value) => total + value, 0) / minutes.length : null;
  const avgAge =
    ages.length > 0 ? ages.reduce((total, value) => total + value, 0) / ages.length : null;
  const capUsed = team ? getCapUsed(team) : 0;
  const payroll = 112 + capUsed * 0.78;

  return {
    avgAge,
    avgMpg,
    capSpace: Math.max(0, 210 - payroll),
    capUsed,
    payroll,
    rosterCount: roster.length,
  };
}

function getStarPlayer(
  roster: PlayerListItem[],
  summaries: Record<number, PlayerSeasonSummary>,
  teamId: number | undefined,
): StarPlayer | undefined {
  const overrideName = teamId ? starPlayerOverrides[teamId] : undefined;
  if (overrideName) {
    const normalizedOverride = normalizePlayerName(overrideName);
    const overridePlayer = roster.find(
      (player) => normalizePlayerName(player.full_name) === normalizedOverride,
    );
    if (overridePlayer) {
      return { player: overridePlayer, summary: summaries[overridePlayer.nba_player_id] };
    }
  }

  let best: StarPlayer | undefined;
  let bestPoints = -Infinity;

  for (const player of roster) {
    const summary = summaries[player.nba_player_id];
    const points = summary?.points_per_game;
    if (typeof points !== "number" || points <= bestPoints) {
      continue;
    }
    best = { player, summary };
    bestPoints = points;
  }

  return best;
}

function topByStat(
  rows: RosterPlayer[],
  key: "points_per_game" | "assists_per_game" | "rebounds_per_game",
  limit: number,
): RosterPlayer[] {
  return [...rows]
    .filter((row) => typeof row.summary?.[key] === "number")
    .sort((left, right) => (right.summary?.[key] ?? 0) - (left.summary?.[key] ?? 0))
    .slice(0, limit);
}

function getTeamFacts(team: Team): TeamFacts {
  const configured = teamFacts[team.nba_team_id] ?? {};
  const historyEntry = teamHistories[team.nba_team_id];
  const foundedMatch = historyEntry?.era.match(/\b(19|20)\d{2}\b/);

  return {
    arena: configured.arena ?? "Home arena",
    founded: configured.founded ?? foundedMatch?.[0] ?? "TBD",
    location: configured.location ?? team.city,
    nickname: configured.nickname ?? team.name,
    owner: teamOwners[team.nba_team_id] ?? configured.owner ?? "Ownership group",
  };
}

function getTeamLogoMotif(team: Team): TeamLogoMotif {
  return teamLogoMotifs[team.nba_team_id] ?? "star";
}

function getCompositionColor(index: number, teamTheme: TeamTheme): string {
  const colors = [
    teamTheme.primary,
    teamTheme.accent,
    "#ffffff",
    `color-mix(in srgb, ${teamTheme.primary} 68%, #ffffff)`,
    `color-mix(in srgb, ${teamTheme.accent} 72%, #071423)`,
  ];
  return colors[index % colors.length];
}

function getCompositionGradient(
  composition: { count: number; group: string }[],
  teamTheme: TeamTheme,
): string {
  const total = composition.reduce((sum, entry) => sum + entry.count, 0);
  if (total <= 0) {
    return "conic-gradient(rgba(138, 161, 194, 0.22) 0deg 360deg)";
  }

  let cursor = 0;
  const stops = composition.map((entry, index) => {
    const start = cursor;
    const end = cursor + (entry.count / total) * 360;
    cursor = end;
    return `${getCompositionColor(index, teamTheme)} ${start.toFixed(1)}deg ${end.toFixed(1)}deg`;
  });

  return `conic-gradient(${stops.join(", ")})`;
}

function clearHoverTimer(timer: MutableRefObject<ReturnType<typeof setTimeout> | null>) {
  if (timer.current) {
    clearTimeout(timer.current);
    timer.current = null;
  }
}

function getCapUsed(team: Team): number {
  if (team.nba_team_id === defaultSelectedTeamId) {
    return 87;
  }
  return 72 + (team.nba_team_id % 22);
}

function getHeadCoach(team: Team | undefined): string {
  return team ? (headCoachesByTeam[team.nba_team_id] ?? "Staff TBD") : "Staff TBD";
}

function getPositionGroup(position: string | null | undefined): string {
  if (!position) {
    return "Unlisted";
  }
  const normalized = position.toLowerCase();
  if (normalized.includes("guard") && normalized.includes("forward")) {
    return "Guard-Forward";
  }
  if (normalized.includes("forward") && normalized.includes("center")) {
    return "Forward-Center";
  }
  if (normalized.includes("guard")) {
    return "Guard";
  }
  if (normalized.includes("forward")) {
    return "Forward";
  }
  if (normalized.includes("center")) {
    return "Center";
  }
  return "Unlisted";
}

function isTwoWayPlayer(player: PlayerListItem): boolean {
  const teamId = player.team?.nba_team_id;
  if (!teamId) {
    return false;
  }
  const names = twoWayPlayersByTeam[teamId];
  if (!names) {
    return false;
  }
  const normalizedFullName = normalizePlayerName(player.full_name);
  return names.some((name) => normalizePlayerName(name) === normalizedFullName);
}

function normalizePlayerName(name: string): string {
  return name.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[.']/g, "").toLowerCase().trim();
}

export function getTeamMeta(team: Team): { conference: "East" | "West"; division: string } {
  const atlantic = new Set([1610612738, 1610612751, 1610612752, 1610612755, 1610612761]);
  const central = new Set([1610612741, 1610612739, 1610612765, 1610612754, 1610612749]);
  const southeast = new Set([1610612737, 1610612766, 1610612748, 1610612753, 1610612764]);
  const northwest = new Set([1610612743, 1610612750, 1610612760, 1610612757, 1610612762]);
  const pacific = new Set([1610612744, 1610612746, 1610612747, 1610612756, 1610612758]);

  if (atlantic.has(team.nba_team_id)) {
    return { conference: "East", division: "Atlantic" };
  }
  if (central.has(team.nba_team_id)) {
    return { conference: "East", division: "Central" };
  }
  if (southeast.has(team.nba_team_id)) {
    return { conference: "East", division: "Southeast" };
  }
  if (northwest.has(team.nba_team_id)) {
    return { conference: "West", division: "Northwest" };
  }
  if (pacific.has(team.nba_team_id)) {
    return { conference: "West", division: "Pacific" };
  }
  return { conference: "West", division: "Southwest" };
}

export function getTeamName(team: Team): string {
  return `${team.city} ${team.name}`;
}

export function getTeamTheme(team: Team | undefined): TeamTheme {
  return team ? (teamThemes[team.nba_team_id] ?? defaultTheme) : defaultTheme;
}

export function getTeamThemeStyle(teamTheme: TeamTheme): CSSProperties {
  return {
    "--roster-primary": teamTheme.primary,
    "--roster-accent": teamTheme.accent,
    "--roster-glow": teamTheme.glow,
    "--roster-muted": teamTheme.muted,
    "--roster-border": teamTheme.border,
    "--team-primary": teamTheme.primary,
    "--team-accent": teamTheme.accent,
    "--team-text": teamTheme.accent,
    "--team-glow": teamTheme.glow,
    "--team-muted": teamTheme.muted,
  } as CSSProperties;
}

function theme(primary: string, accent: string): TeamTheme {
  return {
    primary,
    accent,
    glow: toRgba(accent, 0.22),
    muted: toRgba(primary, 0.22),
    border: toRgba(accent, 0.65),
  };
}

function history(era: string, overview: string, highlights: string[]): TeamHistory {
  return { era, highlights, overview };
}

function toRgba(hex: string, alpha: number): string {
  if (!hex.startsWith("#") || hex.length !== 7) {
    return `rgba(79, 131, 255, ${alpha})`;
  }

  const red = Number.parseInt(hex.slice(1, 3), 16);
  const green = Number.parseInt(hex.slice(3, 5), 16);
  const blue = Number.parseInt(hex.slice(5, 7), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function formatNumber(value: number | null | undefined): string {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(1) : "--";
}

function formatAge(birthdate: string | null | undefined): string {
  const age = calculateAge(birthdate);
  return typeof age === "number" ? String(age) : "--";
}

function calculateAge(birthdate: string | null | undefined): number | null {
  if (!birthdate) {
    return null;
  }
  const birth = new Date(`${birthdate}T00:00:00`);
  if (Number.isNaN(birth.getTime())) {
    return null;
  }
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const monthDelta = today.getMonth() - birth.getMonth();
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < birth.getDate())) {
    age -= 1;
  }
  return age;
}

function formatWeight(weight: number | null | undefined): string {
  return typeof weight === "number" ? `${weight} lbs` : "--";
}

function getPositionAbbreviation(position: string | null | undefined): string {
  const group = getPositionGroup(position);
  if (group === "Guard-Forward") {
    return "G/F";
  }
  if (group === "Forward-Center") {
    return "F/C";
  }
  if (group === "Unlisted") {
    return "--";
  }
  return group.charAt(0);
}

function getChampionshipSummary(team: Team): string {
  const counts: Record<number, string> = {
    1610612738: "18",
    1610612741: "6",
    1610612742: "1",
    1610612744: "7",
    1610612745: "2",
    1610612747: "17",
    1610612748: "3",
    1610612749: "2",
    1610612755: "3",
    1610612757: "1",
    1610612758: "1",
    1610612759: "5",
    1610612761: "1",
    1610612764: "1",
    1610612765: "3",
  };
  return counts[team.nba_team_id] ?? "0";
}

function scoreFromPercent(
  value: number | null | undefined,
  floor: number,
  ceiling: number,
): number {
  if (typeof value !== "number") {
    return 70;
  }
  return clamp(Math.round(((value - floor) / (ceiling - floor)) * 35 + 62), 55, 99);
}

function scoreFromValue(value: number | null | undefined, floor: number, ceiling: number): number {
  if (typeof value !== "number") {
    return 70;
  }
  return clamp(Math.round(((value - floor) / (ceiling - floor)) * 42 + 55), 50, 99);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}
