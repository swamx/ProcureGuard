"""Seed, reset and verify the Nova Industries demo state in ERPNext.

Usage:
    python scripts/erpnext_seed.py seed     # idempotent: safe to run repeatedly
    python scripts/erpnext_seed.py wait     # block until the ERPNext site is ready
    python scripts/erpnext_seed.py reset    # void Purchase Invoices created after seeding
    python scripts/erpnext_seed.py verify   # print the seeded state

Source of truth for all records: data/enterprise/*.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "enterprise"

ERPNEXT_URL = os.environ.get("ERPNEXT_URL", "http://localhost:8080").rstrip("/")
ERPNEXT_USER = os.environ.get("ERPNEXT_USER", "Administrator")
ERPNEXT_PASSWORD = os.environ.get("ERPNEXT_ADMIN_PASSWORD", "admin")

CUSTOM_FIELDS = [
    {
        "dt": "Supplier",
        "fieldname": "procureguard_vendor_id",
        "label": "Vendor ID",
        "fieldtype": "Data",
        "unique": 1,
        "in_standard_filter": 1,
        "insert_after": "supplier_name",
    },
    {
        "dt": "Supplier",
        "fieldname": "registered_email_domain",
        "label": "Registered Email Domain",
        "fieldtype": "Data",
        "insert_after": "procureguard_vendor_id",
    },
    {
        "dt": "Purchase Order",
        "fieldname": "po_number",
        "label": "PO Number",
        "fieldtype": "Data",
        "unique": 1,
        "in_standard_filter": 1,
        "insert_after": "supplier",
    },
]


def load(name: str) -> Any:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


class ERPNext:
    def __init__(self, url: str, user: str, password: str) -> None:
        self.url = url
        self.session = requests.Session()
        response = self.session.post(
            f"{url}/api/method/login", data={"usr": user, "pwd": password}, timeout=30
        )
        self._check(response)

    @staticmethod
    def _check(response: requests.Response) -> Any:
        if not response.ok:
            detail = response.text[:2000]
            raise RuntimeError(f"{response.request.method} {response.url} -> {response.status_code}\n{detail}")
        return response.json() if response.content else {}

    def get_list(self, doctype: str, filters: list | None = None, fields: list | None = None) -> list[dict]:
        params = {
            "filters": json.dumps(filters or []),
            "fields": json.dumps(fields or ["name"]),
            "limit_page_length": 0,
        }
        response = self.session.get(f"{self.url}/api/resource/{doctype}", params=params, timeout=30)
        return self._check(response)["data"]

    def find(self, doctype: str, filters: list) -> str | None:
        rows = self.get_list(doctype, filters)
        return rows[0]["name"] if rows else None

    def get_doc(self, doctype: str, name: str) -> dict:
        response = self.session.get(f"{self.url}/api/resource/{doctype}/{name}", timeout=30)
        return self._check(response)["data"]

    def insert(self, doc: dict) -> dict:
        response = self.session.post(f"{self.url}/api/resource/{doc['doctype']}", json=doc, timeout=60)
        return self._check(response)["data"]

    def call(self, method: str, **kwargs: Any) -> Any:
        response = self.session.post(f"{self.url}/api/method/{method}", json=kwargs, timeout=300)
        return self._check(response).get("message")

    def cancel(self, doctype: str, name: str) -> None:
        self.call("frappe.client.cancel", doctype=doctype, name=name)

    def delete(self, doctype: str, name: str) -> None:
        response = self.session.delete(f"{self.url}/api/resource/{doctype}/{name}", timeout=60)
        self._check(response)


def ensure(erp: ERPNext, doctype: str, filters: list, doc: dict, label: str, submit: bool = False) -> str:
    existing = erp.find(doctype, filters)
    if existing:
        print(f"  = {doctype}: {label}")
        return existing
    created = erp.insert({"doctype": doctype, **doc})
    if submit:
        # Inserting with docstatus=1 skips ERPNext's status update (a PO stays "Draft"),
        # so insert as draft and submit explicitly.
        created = erp.call("frappe.client.submit", doc=created)
    print(f"  + {doctype}: {label}")
    return created["name"]


def setup_company(erp: ERPNext, company: dict) -> None:
    settings = erp.get_doc("System Settings", "System Settings")
    if settings.get("setup_complete"):
        if not erp.find("Company", [["company_name", "=", company["company_name"]]]):
            raise RuntimeError(
                f"Setup wizard is complete but company '{company['company_name']}' does not exist. "
                "Run `make erp-rebuild` for a clean site."
            )
        print("  = Setup wizard already complete")
        return

    print("  Running setup wizard (takes a minute)...")
    result = erp.call(
        "frappe.desk.page.setup_wizard.setup_wizard.setup_complete",
        args={
            "language": "English",
            "country": company["country"],
            "timezone": company["timezone"],
            "currency": company["currency"],
            "full_name": "Nova AP Admin",
            "email": "ap.admin@nova-industries.example",
            "password": ERPNEXT_PASSWORD,
            "company_name": company["company_name"],
            "company_abbr": company["company_abbr"],
            "chart_of_accounts": "Standard",
            "fy_start_date": company["fiscal_year_start"],
            "fy_end_date": company["fiscal_year_end"],
            "setup_demo": 0,
            "enable_telemetry": 0,
        },
    )
    if isinstance(result, dict) and result.get("status") not in (None, "ok", "registered"):
        raise RuntimeError(f"Setup wizard failed: {json.dumps(result)[:2000]}")
    for _ in range(60):
        if erp.find("Company", [["company_name", "=", company["company_name"]]]):
            print(f"  + Company: {company['company_name']}")
            return
        time.sleep(5)
    raise RuntimeError("Setup wizard did not create the company within 5 minutes")


def pick_group(erp: ERPNext, doctype: str, preferred: str, fallback: str) -> str:
    return preferred if erp.find(doctype, [["name", "=", preferred]]) else fallback


def seed(erp: ERPNext) -> None:
    company = load("company")
    vendors = load("vendors")
    by_vendor_id = {v["vendor_id"]: v for v in vendors}
    item = company["item"]

    print("Company")
    setup_company(erp, company)

    print("Custom fields")
    for field in CUSTOM_FIELDS:
        ensure(
            erp,
            "Custom Field",
            [["dt", "=", field["dt"]], ["fieldname", "=", field["fieldname"]]],
            field,
            f"{field['dt']}.{field['fieldname']}",
        )

    print("Master data")
    ensure(erp, "Bank", [["name", "=", company["bank"]]], {"bank_name": company["bank"]}, company["bank"])
    ensure(
        erp,
        "Item",
        [["item_code", "=", item["item_code"]]],
        {
            "item_code": item["item_code"],
            "item_name": item["item_name"],
            "item_group": pick_group(erp, "Item Group", item["item_group"], "All Item Groups"),
            "stock_uom": item["uom"],
            "is_stock_item": 0,
            "is_purchase_item": 1,
        },
        item["item_code"],
    )
    supplier_group = pick_group(erp, "Supplier Group", "Services", "All Supplier Groups")

    print("Vendors")
    for vendor in vendors:
        supplier = ensure(
            erp,
            "Supplier",
            [["procureguard_vendor_id", "=", vendor["vendor_id"]]],
            {
                "supplier_name": vendor["name"],
                "supplier_group": supplier_group,
                "supplier_type": "Company",
                "country": company["country"],
                "default_currency": vendor["currency"],
                "procureguard_vendor_id": vendor["vendor_id"],
                "registered_email_domain": vendor["registered_domain"],
                "on_hold": 1 if vendor["status"] == "BLOCKED" else 0,
                "hold_type": "All" if vendor["status"] == "BLOCKED" else "",
            },
            f"{vendor['vendor_id']} {vendor['name']}",
        )
        vendor["_supplier"] = supplier
        ensure(
            erp,
            "Bank Account",
            [["party_type", "=", "Supplier"], ["party", "=", supplier]],
            {
                "account_name": f"{vendor['name']} Operating",
                "bank": company["bank"],
                "party_type": "Supplier",
                "party": supplier,
                "bank_account_no": vendor["bank_account_no"],
                "is_default": 1,
            },
            f"bank ****{vendor['bank_account_no'][-4:]}",
        )
        ensure(
            erp,
            "Contact",
            [["email_id", "=", vendor["contact_email"]]],
            {
                "first_name": vendor["contact_name"],
                "email_ids": [{"email_id": vendor["contact_email"], "is_primary": 1}],
                "phone_nos": [{"phone": vendor["contact_phone"], "is_primary_phone": 1}],
                "links": [{"link_doctype": "Supplier", "link_name": supplier}],
            },
            vendor["contact_email"],
        )

    def item_rows(lines: list[dict], schedule_date: str | None = None) -> list[dict]:
        rows = []
        for line in lines:
            row = {
                "item_code": item["item_code"],
                "description": line["description"],
                "qty": line["qty"],
                "rate": line["rate"],
                "uom": item["uom"],
            }
            if schedule_date:
                row["schedule_date"] = schedule_date
            rows.append(row)
        return rows

    print("Purchase orders")
    for po in load("purchase_orders"):
        vendor = by_vendor_id[po["vendor_id"]]
        ensure(
            erp,
            "Purchase Order",
            [["po_number", "=", po["po_number"]], ["docstatus", "=", 1]],
            {
                "supplier": vendor["_supplier"],
                "company": company["company_name"],
                "po_number": po["po_number"],
                "transaction_date": po["transaction_date"],
                "schedule_date": po["schedule_date"],
                "currency": po["currency"],
                "items": item_rows(po["lines"], po["schedule_date"]),
            },
            f"{po['po_number']} ({vendor['name']})",
            submit=True,
        )

    print("Previously booked invoices")
    for invoice in load("previous_invoices"):
        vendor = by_vendor_id[invoice["vendor_id"]]
        ensure(
            erp,
            "Purchase Invoice",
            [["supplier", "=", vendor["_supplier"]], ["bill_no", "=", invoice["invoice_number"]], ["docstatus", "=", 1]],
            {
                "supplier": vendor["_supplier"],
                "company": company["company_name"],
                "bill_no": invoice["invoice_number"],
                "bill_date": invoice["invoice_date"],
                "posting_date": invoice["posting_date"],
                "set_posting_time": 1,
                "currency": invoice["currency"],
                "items": item_rows(invoice["lines"]),
            },
            f"{invoice['invoice_number']} ({vendor['name']})",
            submit=True,
        )
    print("Seed complete.")


def reset(erp: ERPNext) -> None:
    """Void Purchase Invoices that are not part of the seed, so demo cases can run again.

    Submitted invoices are cancelled (ERPNext keeps them because they have ledger entries);
    drafts are deleted. For a completely clean ERPNext, use `make erp-rebuild`.
    """
    seeded = {inv["invoice_number"] for inv in load("previous_invoices")}
    invoices = erp.get_list("Purchase Invoice", fields=["name", "bill_no", "docstatus"])
    changed = 0
    for invoice in invoices:
        label = f"Purchase Invoice {invoice['name']} (bill_no={invoice.get('bill_no')})"
        if invoice["docstatus"] == 1 and invoice.get("bill_no") not in seeded:
            erp.cancel("Purchase Invoice", invoice["name"])
            print(f"  x cancelled {label}")
            changed += 1
        elif invoice["docstatus"] == 0:
            erp.delete("Purchase Invoice", invoice["name"])
            print(f"  - deleted {label}")
            changed += 1
    print(f"Reset complete: {changed} invoice(s) voided.")


def wait(url: str, timeout_s: int = 900) -> None:
    """Block until the ERPNext app is installed on the site (site creation takes a few minutes).

    Logins work as soon as Frappe is installed, before ERPNext is, so readiness is checked
    by looking for an ERPNext doctype rather than by logging in.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            erp = ERPNext(url, ERPNEXT_USER, ERPNEXT_PASSWORD)
            if erp.find("DocType", [["name", "=", "Company"]]):
                print("ERPNext is ready.")
                return
        except (requests.RequestException, RuntimeError):
            pass
        time.sleep(10)
    raise RuntimeError(f"ERPNext at {url} not ready after {timeout_s}s")


def verify(erp: ERPNext) -> None:
    suppliers = erp.get_list(
        "Supplier", fields=["name", "procureguard_vendor_id", "registered_email_domain", "on_hold"]
    )
    accounts = {a["party"]: a["bank_account_no"] for a in erp.get_list(
        "Bank Account", [["party_type", "=", "Supplier"]], ["party", "bank_account_no"]
    )}
    print("Suppliers:")
    for s in sorted(suppliers, key=lambda s: s.get("procureguard_vendor_id") or ""):
        bank = accounts.get(s["name"], "")
        hold = "  ON HOLD" if s["on_hold"] else ""
        print(f"  {s['procureguard_vendor_id']}  {s['name']:<28} {s['registered_email_domain']:<26} ****{bank[-4:]}{hold}")
    print("Purchase orders:")
    for po in erp.get_list(
        "Purchase Order", [["docstatus", "=", 1]], ["po_number", "supplier", "grand_total", "status"]
    ):
        print(f"  {po['po_number']:<10} {po['supplier']:<28} {po['grand_total']:>10,.2f}  {po['status']}")
    print("Purchase invoices:")
    for inv in erp.get_list("Purchase Invoice", fields=["name", "bill_no", "supplier", "grand_total", "docstatus"]):
        print(f"  {inv['bill_no']:<14} {inv['supplier']:<28} {inv['grand_total']:>10,.2f}  docstatus={inv['docstatus']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["wait", "seed", "reset", "verify"])
    args = parser.parse_args()
    if args.command == "wait":
        wait(ERPNEXT_URL)
        return 0
    erp = ERPNext(ERPNEXT_URL, ERPNEXT_USER, ERPNEXT_PASSWORD)
    {"seed": seed, "reset": reset, "verify": verify}[args.command](erp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
