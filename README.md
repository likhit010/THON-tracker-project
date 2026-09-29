# 💛💙 THON Fundraising Tracker

A command-line app for tracking fundraising for **THON**, Penn State's student-run philanthropy benefiting the Four Diamonds Fund. Organizations, members, and donations (online, canning, cash, and events) are stored in a SQLite database. The app shows live progress bars, leaderboards, milestone alerts, and fundraising analytics.

Built with **Python** (standard library only), **SQL** (SQLite), and **object-oriented design**.

---

## Features

- **Dashboard** with total raised, net after processing fees, totals by donation type, top canning locations, and a daily trend sparkline
- **Organization leaderboard** with color-coded progress bars toward each org's goal
- **Top fundraisers** ranked across all organizations, with percent of personal goal
- **Milestone alerts** 🎉 when a donation pushes an org past 25%, 50%, 75%, or 100%
- **Input validation**, including PSU Access ID format, positive amounts, and required canning locations
- **Demo mode** that loads realistic sample data in one command

## Quick start

```bash
git clone https://github.com/<your-username>/thon-fundraising-tracker.git
cd thon-fundraising-tracker
python main.py --demo      # loads sample data, then opens the menu
```

No packages to install. Requires Python 3.10+.

Run the tests:

```bash
python -m unittest discover tests -v
```

## Project structure

```
thon_tracker/
├── main.py              # Interactive CLI (TrackerCLI class)
├── seed.py              # Sample data generator
├── tracker/
│   ├── schema.sql       # Tables, constraints, indexes, and a reporting VIEW
│   ├── database.py      # Database class (connection + schema setup)
│   ├── models.py        # Domain classes: Organization, Member, Donation subclasses
│   ├── repositories.py  # SQL CRUD for each table
│   ├── services.py      # Business logic and analytics queries
│   └── display.py       # Terminal tables, progress bars, sparklines
└── tests/
    └── test_tracker.py  # 10 unit tests (in-memory database)
```

## Object-oriented design

| Concept | Where it shows up |
|---|---|
| **Abstraction** | `Entity` and `Donation` are abstract base classes (`abc.ABC`) |
| **Encapsulation** | Validation lives inside each model; `amount` and `goal` are guarded by properties |
| **Inheritance** | `OnlineDonation`, `CanningDonation`, `CashDonation`, and `EventDonation` extend `Donation`; each repository extends `BaseRepository` |
| **Polymorphism** | Every donation type implements `describe()` and `net_amount()` differently (online gifts subtract a processing fee), and `net_total()` treats them all the same |
| **Design patterns** | Factory (`DonationFactory`), Repository, Facade (`FundraisingService`), Template Method (`BaseRepository.add`) |

## Database design

```
organizations 1 ──< members 1 ──< donations
```

- **Constraints:** `CHECK` constraints on types, roles, and amounts; `UNIQUE` Access IDs; foreign keys with `ON DELETE CASCADE`
- **Indexes** on foreign-key columns
- **View:** `org_totals` aggregates each organization's total raised, member count, and donation count using `LEFT JOIN` and `GROUP BY`
- **Queries** in `services.py` use joins, aggregates (`SUM`, `COUNT`), filtering, ordering, and `LIMIT`

## Ideas for future work

- Web dashboard with Flask and Chart.js
- Export reports to CSV
- Per-member donation receipts by email
- Countdown to THON Weekend

---

*For The Kids.* This is a student project and is not affiliated with or endorsed by THON or Penn State.
