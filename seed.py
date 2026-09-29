"""Loads realistic sample data so the app has something to show."""
from __future__ import annotations

import random
from datetime import date, timedelta

from tracker import Database, FundraisingService

ORGS = [
    ("Blue & White Society", "General", 15000),
    ("Engineering Council", "Special Interest", 12000),
    ("Alpha Beta Gamma", "Greek", 20000),
    ("Nittany Dancers", "Independent", 8000),
    ("CS Club", "Special Interest", 6000),
]
FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Chloe", "Owen", "Mia", "Lucas",
         "Ella", "Jack", "Nora", "Ryan", "Leah", "Dylan", "Sofia", "Evan", "Grace", "Caleb"]
LAST = ["Smith", "Patel", "Nguyen", "Kim", "Garcia", "Brown", "Lee", "Miller", "Davis", "Wilson"]
CANNING_SPOTS = ["Pittsburgh", "Philadelphia", "Harrisburg", "Erie", "Scranton", "Allentown", "State College"]
EVENTS = ["Pancake Breakfast", "Trivia Night", "5K Fun Run", "Bake Sale", "Date Auction"]
DONORS = ["Grandma", "Aunt Linda", "Mr. Thompson", "Family friend", None, None, "Local business"]


def seed(service: FundraisingService, rng_seed: int = 46) -> None:
    rng = random.Random(rng_seed)
    used_ids = set()
    start = date.today() - timedelta(days=20)

    for name, org_type, goal in ORGS:
        org = service.create_organization(name, org_type, goal)
        for i in range(rng.randint(4, 7)):
            first, last = rng.choice(FIRST), rng.choice(LAST)
            while True:
                aid = f"{first[0]}{last[0]}{rng.choice('abcdefghjkmnprstwxyz')}{rng.randint(1, 9999)}".lower()
                if aid not in used_ids:
                    used_ids.add(aid)
                    break
            role = "Chair" if i == 0 else rng.choices(["Member", "Dancer"], [4, 1])[0]
            member = service.add_member(org.id, first, last, aid, role, rng.choice([250, 300, 500]))

            for _ in range(rng.randint(2, 8)):
                day = (start + timedelta(days=rng.randint(0, 20))).isoformat()
                kind = rng.choices(["Online", "Canning", "Cash", "Event"], [5, 3, 1, 1])[0]
                amount = round(rng.uniform(10, 150) if kind != "Canning" else rng.uniform(40, 400), 2)
                loc = rng.choice(CANNING_SPOTS) if kind == "Canning" else rng.choice(EVENTS) if kind == "Event" else None
                donor = rng.choice(DONORS) if kind in ("Online", "Cash") else None
                service.record_donation(member.id, kind, amount, donor, loc, day)


if __name__ == "__main__":
    with Database("thon.db") as db:
        s = FundraisingService(db)
        if s.orgs.count():
            print("Database already has data; delete thon.db to reseed.")
        else:
            seed(s)
            print(f"Seeded {s.orgs.count()} orgs, {s.members.count()} members, "
                  f"{s.donations.count()} donations. Total: ${s.grand_total():,.2f}")
