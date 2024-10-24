# Data Model Diagrams

## Legend
Crows feet notation for ERDs

```mermaid

erDiagram
    LEGEND1 ||--|| LEGEND2 : "one-to-one"
    LEGEND3 ||--o| LEGEND4 : "one-to-zero-or-one"
    LEGEND5 ||--|{ LEGEND6 : "one-to-many"
    LEGEND7 ||--o{ LEGEND8 : "one-to-zero-or-many"
    LEGEND9 }|--|{ LEGEND10 : "many-to-many"
```

## Sources

### MySportsFeeds API

#### Daily DFS Endpoint
This endpoint is consumed as JSON
```mermaid

erDiagram
    DFS_FEED ||--o{ SOURCE : contains
    SOURCE ||--o{ SLATE : contains
    SLATE ||--o{ GAME : contains
    SLATE ||--o{ CONTEST : contains
    SLATE ||--o{ PLAYER : contains
    PLAYER ||--|| TEAM : belongs_to
    PLAYER ||--|| GAME : scheduled_in

    DFS_FEED {
        datetime lastUpdatedOn "2024-10-18T17:50:06.685Z"
    }

    SOURCE {
        string source "DraftKings"
    }

    SLATE {
        date forDate "2024-10-08T04:00:00.000Z"
        int forWeek "null for NHL"
        string identifier "114407"
        string label "Featured"
        string type "Classic"
        datetime minGameStart "2024-10-08T20:30:00.000Z"
    }

    GAME {
        int id
        datetime startTime
        string awayTeamAbbreviation
        string homeTeamAbbreviation
    }

    CONTEST {
        string identifier "167971213"
        string label "NHL $150K Opening Night Puck Drop [$50K to 1st]"
        string type "Classic"
        float entryFee "5.0"
        float totalPrizePool "150000"
        int maxOverallEntries "35671"
        int maxEntriesPerUser "150"
    }

    PLAYER {
        string sourceId
        string sourceFirstName
        string sourceLastName
        string sourceTeam
        string sourcePosition
        array rosterSlots
        int salary
        float fantasyPoints
        int teamId
        string teamAbbreviation
        int playerId
        string firstName
        string lastName
        string position
        int jerseyNumber
    }

    TEAM {
        int id
        string abbreviation
    }

```

#### DFS Projections Endpoint
This endpoint is consumed as JSON

```mermaid
erDiagram
    PROJECTIONS_FEED ||--o{ PROJECTION : contains
    PROJECTION ||--|| PLAYER : projects
    PROJECTION ||--|| TEAM : plays_for
    PROJECTION ||--|| GAME : scheduled_in
    PROJECTION ||--o{ FANTASY_POINTS : has

    PROJECTIONS_FEED {
        datetime lastUpdatedOn "2024-09-02T03:19:38.265Z"
    }

    PROJECTION {
        int playerId
        string firstName
        string lastName
        string position
        int jerseyNumber
        int teamId
        string teamAbbreviation
        int gameId
    }

    PLAYER {
        int id
        string firstName
        string lastName
        string position
        int jerseyNumber
    }

    TEAM {
        int id
        string abbreviation
    }

    GAME {
        int id
        datetime startTime
        string awayTeamAbbreviation
        string homeTeamAbbreviation
    }

    FANTASY_POINTS {
        string source "DraftKings, FanDuel, FantasyDraft, Yahoo"
        float points "6.30, 7.20, 0.00, 5.40"
    }

```