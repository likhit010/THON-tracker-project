-- THON Fundraising Tracker schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
    org_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    org_type    TEXT    NOT NULL CHECK (org_type IN ('General', 'Special Interest', 'Greek', 'Independent')),
    goal        REAL    NOT NULL CHECK (goal > 0),
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS members (
    member_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id      INTEGER NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    first_name  TEXT    NOT NULL,
    last_name   TEXT    NOT NULL,
    access_id   TEXT    NOT NULL UNIQUE,          -- PSU Access ID, e.g. abc1234
    role        TEXT    NOT NULL DEFAULT 'Member' CHECK (role IN ('Member', 'Chair', 'Dancer')),
    personal_goal REAL  NOT NULL DEFAULT 250 CHECK (personal_goal >= 0)
);

CREATE TABLE IF NOT EXISTS donations (
    donation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id     INTEGER NOT NULL REFERENCES members(member_id) ON DELETE CASCADE,
    donation_type TEXT    NOT NULL CHECK (donation_type IN ('Online', 'Canning', 'Cash', 'Event')),
    amount        REAL    NOT NULL CHECK (amount > 0),
    donor_name    TEXT,
    location      TEXT,                           -- canning location or event name
    donated_on    TEXT    NOT NULL DEFAULT (date('now'))
);

CREATE INDEX IF NOT EXISTS idx_members_org      ON members(org_id);
CREATE INDEX IF NOT EXISTS idx_donations_member ON donations(member_id);

-- Convenience view: total raised per organization
CREATE VIEW IF NOT EXISTS org_totals AS
SELECT o.org_id,
       o.name,
       o.org_type,
       o.goal,
       COALESCE(SUM(d.amount), 0)            AS raised,
       COUNT(DISTINCT m.member_id)           AS member_count,
       COUNT(d.donation_id)                  AS donation_count
FROM organizations o
LEFT JOIN members   m ON m.org_id    = o.org_id
LEFT JOIN donations d ON d.member_id = m.member_id
GROUP BY o.org_id;
