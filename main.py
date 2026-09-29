"""THON Fundraising Tracker - interactive command-line app.

Run:  python main.py            (uses thon.db)
      python main.py --demo     (loads sample data first)
"""
from __future__ import annotations

import argparse

from tracker import Database, FundraisingService
from tracker.display import banner, money, progress_bar, spark, table
from tracker.models import DonationFactory, Member, Organization, ValidationError


class TrackerCLI:
    """Menu-driven interface. Each menu option maps to one method."""

    def __init__(self, service: FundraisingService):
        self.s = service
        self.menu = {
            "1": ("Dashboard", self.dashboard),
            "2": ("Organization leaderboard", self.leaderboard),
            "3": ("Top fundraisers", self.top_fundraisers),
            "4": ("Record a donation", self.record_donation),
            "5": ("Add a member", self.add_member),
            "6": ("Add an organization", self.add_org),
            "7": ("View organization details", self.org_details),
            "8": ("Recent donations", self.recent),
            "q": ("Quit", None),
        }

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        print(banner("THON Fundraising Tracker  FTK!"))
        while True:
            print()
            for key, (label, _) in self.menu.items():
                print(f"  [{key}] {label}")
            choice = input("\nChoose an option: ").strip().lower()
            if choice == "q":
                print("For The Kids! 💛💙")
                return
            action = self.menu.get(choice, (None, None))[1]
            if action is None:
                print("Invalid option.")
                continue
            try:
                action()
            except ValidationError as e:
                print(f"⚠  {e}")
            except ValueError:
                print("⚠  Please enter a valid number.")

    # ----------------------------- views ------------------------------ #
    def dashboard(self) -> None:
        print(banner("Dashboard"))
        print(f"  Total raised:      {money(self.s.grand_total())}")
        print(f"  After fees (net):  {money(self.s.net_total())}")
        print(f"  Organizations:     {self.s.orgs.count()}")
        print(f"  Members:           {self.s.members.count()}")
        print(f"  Donations:         {self.s.donations.count()}\n")

        print(table(["Type", "Total", "Count"],
                    [(t, money(v), n) for t, v, n in self.s.totals_by_type()], "lrr"))
        print()
        canning = self.s.top_canning_locations()
        if canning:
            print(table(["Top canning location", "Total", "Trips"],
                        [(l, money(v), n) for l, v, n in canning], "lrr"))
        daily = self.s.daily_totals()
        if daily:
            print(f"\n  Daily trend ({daily[0][0]} → {daily[-1][0]}): {spark([v for _, v in daily])}")

    def leaderboard(self) -> None:
        print(banner("Organization Leaderboard"))
        for i, p in enumerate(self.s.org_leaderboard(), 1):
            print(f" {i:>2}. {p.name:<28} {money(p.raised):>12} / {money(p.goal):<12}")
            print(f"     {progress_bar(p.percent)}")

    def top_fundraisers(self) -> None:
        print(banner("Top Fundraisers"))
        rows = [(i, m.name, m.org_name, m.role, money(m.raised), f"{m.percent:.0f}%")
                for i, m in enumerate(self.s.top_fundraisers(10), 1)]
        print(table(["#", "Name", "Organization", "Role", "Raised", "Goal %"], rows, "rllllr"))

    def org_details(self) -> None:
        org_id = self._pick_org()
        p = self.s.org_progress(org_id)
        print(banner(p.name))
        print(f"  {progress_bar(p.percent, 40)}")
        print(f"  Raised {money(p.raised)} of {money(p.goal)}  ·  {money(p.remaining)} to go\n")
        rows = [(m.name, m.role, money(m.raised), money(m.personal_goal), f"{m.percent:.0f}%")
                for m in self.s.top_fundraisers(1000, org_id)]
        print(table(["Member", "Role", "Raised", "Goal", "%"], rows, "llrrr"))
        behind = self.s.members_below_goal(org_id)
        if behind:
            print(f"\n  {len(behind)} member(s) still working toward their personal goal.")

    def recent(self) -> None:
        print(banner("Recent Donations"))
        for d in self.s.donations.recent(10):
            m = self.s.members.get(d.member_id)
            print(f"  {d.donated_on}  {d.describe():<45}  via {m.full_name}")

    # ----------------------------- inputs ----------------------------- #
    def record_donation(self) -> None:
        access_id = input("Member Access ID (e.g. abc1234): ").strip()
        member = self.s.members.find_by_access_id(access_id)
        if member is None:
            raise ValidationError(f"No member with Access ID '{access_id}'.")
        dtype = self._choose("Donation type", DonationFactory.types())
        amount = float(input("Amount: $"))
        donor = location = None
        if dtype in ("Online", "Cash"):
            donor = input("Donor name (blank = anonymous): ").strip() or None
        else:
            location = input("Canning location: " if dtype == "Canning" else "Event name: ").strip()
        donation, crossed = self.s.record_donation(member.id, dtype, amount, donor, location)
        print(f"✅ Saved: {donation.describe()} for {member.full_name}")
        for m in crossed:
            print(f"🎉 Milestone! The organization just passed {m}% of its goal!")

    def add_member(self) -> None:
        org_id = self._pick_org()
        first = input("First name: ")
        last = input("Last name: ")
        access_id = input("Access ID: ")
        role = self._choose("Role", Member.VALID_ROLES)
        goal = float(input("Personal goal ($, default 250): ") or 250)
        m = self.s.add_member(org_id, first, last, access_id, role, goal)
        print(f"✅ Added {m.full_name} ({m.email})")

    def add_org(self) -> None:
        name = input("Organization name: ")
        org_type = self._choose("Type", Organization.VALID_TYPES)
        goal = float(input("Fundraising goal: $"))
        o = self.s.create_organization(name, org_type, goal)
        print(f"✅ Created {o.name} (id {o.id})")

    # ----------------------------- helpers ---------------------------- #
    def _pick_org(self) -> int:
        orgs = self.s.orgs.all()
        if not orgs:
            raise ValidationError("No organizations yet. Add one first.")
        for o in orgs:
            print(f"  [{o.id}] {o.name}")
        return int(input("Organization id: "))

    @staticmethod
    def _choose(prompt: str, options) -> str:
        for i, opt in enumerate(options, 1):
            print(f"  [{i}] {opt}")
        idx = int(input(f"{prompt}: ")) - 1
        if not 0 <= idx < len(options):
            raise ValidationError("Invalid choice.")
        return options[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="THON Fundraising Tracker")
    parser.add_argument("--db", default="thon.db", help="SQLite database file")
    parser.add_argument("--demo", action="store_true", help="load sample data (if empty)")
    args = parser.parse_args()

    with Database(args.db) as db:
        service = FundraisingService(db)
        if args.demo and service.orgs.count() == 0:
            from seed import seed
            seed(service)
            print("Loaded demo data.")
        TrackerCLI(service).run()


if __name__ == "__main__":
    main()
