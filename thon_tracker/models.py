"""Domain models for the THON Fundraising Tracker.

OOP concepts shown here:
  * Abstraction   - Entity and Donation are abstract base classes.
  * Encapsulation - validation lives inside each class; amounts are
                    exposed through read-only properties.
  * Inheritance   - OnlineDonation, CanningDonation, etc. extend Donation.
  * Polymorphism  - every Donation subclass implements describe() and
                    net_amount() differently, but callers treat them the same.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional


class ValidationError(ValueError):
    """Raised when a model receives invalid data."""


class Entity(ABC):
    """Base class for everything that is stored as a row in the database."""

    def __init__(self, id: Optional[int] = None):
        self.id = id

    @abstractmethod
    def validate(self) -> None:
        """Raise ValidationError if the object is not in a valid state."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} id={self.id}>"


# --------------------------------------------------------------------------- #
# Organization
# --------------------------------------------------------------------------- #
class Organization(Entity):
    VALID_TYPES = ("General", "Special Interest", "Greek", "Independent")

    def __init__(self, name: str, org_type: str, goal: float, id: Optional[int] = None):
        super().__init__(id)
        self.name = name.strip()
        self.org_type = org_type
        self._goal = float(goal)
        self.validate()

    @property
    def goal(self) -> float:
        return self._goal

    @goal.setter
    def goal(self, value: float) -> None:
        if value <= 0:
            raise ValidationError("Goal must be greater than 0.")
        self._goal = float(value)

    def validate(self) -> None:
        if not self.name:
            raise ValidationError("Organization name cannot be empty.")
        if self.org_type not in self.VALID_TYPES:
            raise ValidationError(f"org_type must be one of {self.VALID_TYPES}.")
        if self._goal <= 0:
            raise ValidationError("Goal must be greater than 0.")


# --------------------------------------------------------------------------- #
# Member
# --------------------------------------------------------------------------- #
class Member(Entity):
    VALID_ROLES = ("Member", "Chair", "Dancer")
    ACCESS_ID_PATTERN = re.compile(r"^[a-z]{2,3}\d{1,4}$")  # e.g. abc1234

    def __init__(self, org_id: int, first_name: str, last_name: str, access_id: str,
                 role: str = "Member", personal_goal: float = 250.0, id: Optional[int] = None):
        super().__init__(id)
        self.org_id = org_id
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.access_id = access_id.strip().lower()
        self.role = role
        self.personal_goal = float(personal_goal)
        self.validate()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def email(self) -> str:
        return f"{self.access_id}@psu.edu"

    def validate(self) -> None:
        if not self.first_name or not self.last_name:
            raise ValidationError("Member needs a first and last name.")
        if not self.ACCESS_ID_PATTERN.match(self.access_id):
            raise ValidationError(f"'{self.access_id}' is not a valid PSU Access ID (e.g. abc1234).")
        if self.role not in self.VALID_ROLES:
            raise ValidationError(f"role must be one of {self.VALID_ROLES}.")
        if self.personal_goal < 0:
            raise ValidationError("Personal goal cannot be negative.")


# --------------------------------------------------------------------------- #
# Donations (inheritance + polymorphism)
# --------------------------------------------------------------------------- #
class Donation(Entity):
    """Abstract donation. Subclasses define the type-specific behavior."""

    TYPE: str = ""  # overridden by subclasses

    def __init__(self, member_id: int, amount: float, donor_name: Optional[str] = None,
                 location: Optional[str] = None, donated_on: Optional[str] = None,
                 id: Optional[int] = None):
        super().__init__(id)
        self.member_id = member_id
        self._amount = round(float(amount), 2)
        self.donor_name = donor_name
        self.location = location
        self.donated_on = donated_on or date.today().isoformat()
        self.validate()

    @property
    def amount(self) -> float:
        return self._amount

    @property
    def donation_type(self) -> str:
        return self.TYPE

    def validate(self) -> None:
        if self._amount <= 0:
            raise ValidationError("Donation amount must be positive.")

    @abstractmethod
    def describe(self) -> str:
        """Human-readable one-line description."""

    def net_amount(self) -> float:
        """Amount that actually reaches the Four Diamonds fund (default: all of it)."""
        return self._amount


class OnlineDonation(Donation):
    TYPE = "Online"
    PROCESSING_RATE = 0.029   # illustrative card-processing rate
    PROCESSING_FLAT = 0.30

    def describe(self) -> str:
        who = self.donor_name or "Anonymous"
        return f"Online gift from {who}: ${self.amount:,.2f}"

    def net_amount(self) -> float:
        return round(self.amount - (self.amount * self.PROCESSING_RATE + self.PROCESSING_FLAT), 2)


class CanningDonation(Donation):
    TYPE = "Canning"

    def validate(self) -> None:
        super().validate()
        if not self.location:
            raise ValidationError("Canning donations need a location (e.g. 'Pittsburgh').")

    def describe(self) -> str:
        return f"Canning in {self.location}: ${self.amount:,.2f}"


class CashDonation(Donation):
    TYPE = "Cash"

    def describe(self) -> str:
        who = self.donor_name or "Anonymous"
        return f"Cash/check from {who}: ${self.amount:,.2f}"


class EventDonation(Donation):
    TYPE = "Event"

    def validate(self) -> None:
        super().validate()
        if not self.location:
            raise ValidationError("Event donations need an event name.")

    def describe(self) -> str:
        return f"Event '{self.location}': ${self.amount:,.2f}"


class DonationFactory:
    """Builds the right Donation subclass from a type string (Factory pattern)."""

    _registry = {cls.TYPE: cls for cls in (OnlineDonation, CanningDonation, CashDonation, EventDonation)}

    @classmethod
    def types(cls) -> tuple[str, ...]:
        return tuple(cls._registry)

    @classmethod
    def create(cls, donation_type: str, **kwargs) -> Donation:
        try:
            klass = cls._registry[donation_type]
        except KeyError:
            raise ValidationError(f"Unknown donation type '{donation_type}'. Choose from {cls.types()}.")
        return klass(**kwargs)


# --------------------------------------------------------------------------- #
# Read-only report objects
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class OrgProgress:
    org_id: int
    name: str
    org_type: str
    goal: float
    raised: float
    member_count: int
    donation_count: int

    @property
    def percent(self) -> float:
        return 100 * self.raised / self.goal if self.goal else 0.0

    @property
    def remaining(self) -> float:
        return max(self.goal - self.raised, 0.0)


@dataclass(frozen=True)
class MemberTotal:
    member_id: int
    name: str
    org_name: str
    role: str
    personal_goal: float
    raised: float

    @property
    def percent(self) -> float:
        return 100 * self.raised / self.personal_goal if self.personal_goal else 0.0
