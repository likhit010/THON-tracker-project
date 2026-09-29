"""Business logic and reporting queries (JOINs, GROUP BY, aggregates)."""
from __future__ import annotations

from typing import Optional

from .database import Database
from .models import (DonationFactory, Donation, Member, MemberTotal, Organization,
                     OrgProgress, ValidationError)
from .repositories import DonationRepository, MemberRepository, OrganizationRepository


class FundraisingService:
    """Facade that the CLI (or a future web app) talks to."""

    MILESTONES = (25, 50, 75, 100)

    def __init__(self, db: Database):
        self.db = db
        self.orgs = OrganizationRepository(db)
        self.members = MemberRepository(db)
        self.donations = DonationRepository(db)

    # ----------------------------- commands ----------------------------- #
    def create_organization(self, name: str, org_type: str, goal: float) -> Organization:
        return self.orgs.add(Organization(name, org_type, goal))

    def add_member(self, org_id: int, first: str, last: str, access_id: str,
                   role: str = "Member", personal_goal: float = 250) -> Member:
        if self.orgs.get(org_id) is None:
            raise ValidationError(f"No organization with id {org_id}.")
        return self.members.add(Member(org_id, first, last, access_id, role, personal_goal))

    def record_donation(self, member_id: int, donation_type: str, amount: float,
                        donor_name: Optional[str] = None, location: Optional[str] = None,
                        donated_on: Optional[str] = None) -> tuple[Donation, list[int]]:
        """Save a donation and return any organization milestones it just crossed."""
        member = self.members.get(member_id)
        if member is None:
            raise ValidationError(f"No member with id {member_id}.")

        before = self.org_progress(member.org_id).percent
        donation = DonationFactory.create(donation_type, member_id=member_id, amount=amount,
                                          donor_name=donor_name, location=location,
                                          donated_on=donated_on)
        self.donations.add(donation)
        after = self.org_progress(member.org_id).percent
        crossed = [m for m in self.MILESTONES if before < m <= after]
        return donation, crossed

    # ------------------------------ reports ----------------------------- #
    def org_progress(self, org_id: int) -> OrgProgress:
        rows = self.db.query("SELECT * FROM org_totals WHERE org_id = ?", (org_id,))
        if not rows:
            raise ValidationError(f"No organization with id {org_id}.")
        return OrgProgress(**dict(rows[0]))

    def org_leaderboard(self, org_type: Optional[str] = None) -> list[OrgProgress]:
        sql = "SELECT * FROM org_totals"
        params: tuple = ()
        if org_type:
            sql += " WHERE org_type = ?"
            params = (org_type,)
        sql += " ORDER BY raised DESC, name"
        return [OrgProgress(**dict(r)) for r in self.db.query(sql, params)]

    def top_fundraisers(self, limit: int = 10, org_id: Optional[int] = None) -> list[MemberTotal]:
        sql = """
            SELECT m.member_id,
                   m.first_name || ' ' || m.last_name AS name,
                   o.name                              AS org_name,
                   m.role,
                   m.personal_goal,
                   COALESCE(SUM(d.amount), 0)          AS raised
            FROM members m
            JOIN organizations o ON o.org_id = m.org_id
            LEFT JOIN donations d ON d.member_id = m.member_id
            {where}
            GROUP BY m.member_id
            ORDER BY raised DESC, name
            LIMIT ?
        """
        where, params = ("WHERE m.org_id = ?", (org_id, limit)) if org_id else ("", (limit,))
        rows = self.db.query(sql.format(where=where), params)
        return [MemberTotal(**dict(r)) for r in rows]

    def totals_by_type(self) -> list[tuple[str, float, int]]:
        rows = self.db.query("""
            SELECT donation_type, SUM(amount) AS total, COUNT(*) AS n
            FROM donations GROUP BY donation_type ORDER BY total DESC
        """)
        return [(r["donation_type"], r["total"], r["n"]) for r in rows]

    def top_canning_locations(self, limit: int = 5) -> list[tuple[str, float, int]]:
        rows = self.db.query("""
            SELECT location, SUM(amount) AS total, COUNT(*) AS trips
            FROM donations WHERE donation_type = 'Canning'
            GROUP BY location ORDER BY total DESC LIMIT ?
        """, (limit,))
        return [(r["location"], r["total"], r["trips"]) for r in rows]

    def daily_totals(self, days: int = 14) -> list[tuple[str, float]]:
        rows = self.db.query("""
            SELECT donated_on, SUM(amount) AS total
            FROM donations
            GROUP BY donated_on
            ORDER BY donated_on DESC
            LIMIT ?
        """, (days,))
        return [(r["donated_on"], r["total"]) for r in reversed(rows)]

    def members_below_goal(self, org_id: int) -> list[MemberTotal]:
        return [m for m in self.top_fundraisers(limit=10_000, org_id=org_id)
                if m.raised < m.personal_goal]

    def grand_total(self) -> float:
        return self.db.query("SELECT COALESCE(SUM(amount), 0) AS t FROM donations")[0]["t"]

    def net_total(self) -> float:
        """Total after type-specific fees; uses polymorphic net_amount()."""
        return round(sum(d.net_amount() for d in self.donations.all()), 2)
