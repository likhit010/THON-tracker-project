"""Repository layer: the only place that writes SQL for individual tables.

Each repository inherits shared behavior from BaseRepository and
implements the table-specific pieces (Template Method pattern).
"""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

from .database import Database
from .models import (DonationFactory, Donation, Entity, Member, Organization,
                     ValidationError)

T = TypeVar("T", bound=Entity)


class BaseRepository(ABC, Generic[T]):
    table: str = ""
    pk: str = ""

    def __init__(self, db: Database):
        self.db = db

    # --- hooks each subclass must implement ---
    @abstractmethod
    def _from_row(self, row: sqlite3.Row) -> T: ...

    @abstractmethod
    def _insert_sql(self, obj: T) -> tuple[str, tuple]: ...

    # --- shared behavior ---
    def add(self, obj: T) -> T:
        obj.validate()
        sql, params = self._insert_sql(obj)
        try:
            cur = self.db.execute(sql, params)
        except sqlite3.IntegrityError as e:
            raise ValidationError(f"Could not save {type(obj).__name__}: {e}") from e
        obj.id = cur.lastrowid
        return obj

    def get(self, id: int) -> Optional[T]:
        rows = self.db.query(f"SELECT * FROM {self.table} WHERE {self.pk} = ?", (id,))
        return self._from_row(rows[0]) if rows else None

    def all(self) -> list[T]:
        return [self._from_row(r) for r in self.db.query(f"SELECT * FROM {self.table} ORDER BY {self.pk}")]

    def delete(self, id: int) -> bool:
        cur = self.db.execute(f"DELETE FROM {self.table} WHERE {self.pk} = ?", (id,))
        return cur.rowcount > 0

    def count(self) -> int:
        return self.db.query(f"SELECT COUNT(*) AS n FROM {self.table}")[0]["n"]


class OrganizationRepository(BaseRepository[Organization]):
    table, pk = "organizations", "org_id"

    def _from_row(self, r):
        return Organization(r["name"], r["org_type"], r["goal"], id=r["org_id"])

    def _insert_sql(self, o):
        return ("INSERT INTO organizations (name, org_type, goal) VALUES (?, ?, ?)",
                (o.name, o.org_type, o.goal))

    def find_by_name(self, name: str) -> Optional[Organization]:
        rows = self.db.query("SELECT * FROM organizations WHERE name = ? COLLATE NOCASE", (name,))
        return self._from_row(rows[0]) if rows else None

    def update_goal(self, org_id: int, new_goal: float) -> None:
        if new_goal <= 0:
            raise ValidationError("Goal must be greater than 0.")
        self.db.execute("UPDATE organizations SET goal = ? WHERE org_id = ?", (new_goal, org_id))


class MemberRepository(BaseRepository[Member]):
    table, pk = "members", "member_id"

    def _from_row(self, r):
        return Member(r["org_id"], r["first_name"], r["last_name"], r["access_id"],
                      r["role"], r["personal_goal"], id=r["member_id"])

    def _insert_sql(self, m):
        return ("INSERT INTO members (org_id, first_name, last_name, access_id, role, personal_goal) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (m.org_id, m.first_name, m.last_name, m.access_id, m.role, m.personal_goal))

    def by_org(self, org_id: int) -> list[Member]:
        rows = self.db.query("SELECT * FROM members WHERE org_id = ? ORDER BY last_name", (org_id,))
        return [self._from_row(r) for r in rows]

    def find_by_access_id(self, access_id: str) -> Optional[Member]:
        rows = self.db.query("SELECT * FROM members WHERE access_id = ?", (access_id.lower(),))
        return self._from_row(rows[0]) if rows else None


class DonationRepository(BaseRepository[Donation]):
    table, pk = "donations", "donation_id"

    def _from_row(self, r):
        return DonationFactory.create(
            r["donation_type"], member_id=r["member_id"], amount=r["amount"],
            donor_name=r["donor_name"], location=r["location"],
            donated_on=r["donated_on"], id=r["donation_id"])

    def _insert_sql(self, d):
        return ("INSERT INTO donations (member_id, donation_type, amount, donor_name, location, donated_on) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (d.member_id, d.donation_type, d.amount, d.donor_name, d.location, d.donated_on))

    def by_member(self, member_id: int) -> list[Donation]:
        rows = self.db.query("SELECT * FROM donations WHERE member_id = ? ORDER BY donated_on DESC",
                             (member_id,))
        return [self._from_row(r) for r in rows]

    def recent(self, limit: int = 10) -> list[Donation]:
        rows = self.db.query("SELECT * FROM donations ORDER BY donated_on DESC, donation_id DESC LIMIT ?",
                             (limit,))
        return [self._from_row(r) for r in rows]
