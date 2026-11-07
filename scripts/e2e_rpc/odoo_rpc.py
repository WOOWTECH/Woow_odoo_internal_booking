"""
Odoo XML-RPC helper for the manual end-to-end scripts in this directory.

These scripts are NOT Odoo unit tests (those live in ../../tests) and need a
running Odoo server. Nothing secret is stored here: the server, the database
and every password come from the environment:

    BOOKING_E2E_URL                 default http://localhost:9071
    BOOKING_E2E_DB                  default odoocalendar
    BOOKING_E2E_PASSWORD_<LOGIN>    password of <LOGIN> (upper case, non
                                    alphanumerics as _), e.g.
                                    BOOKING_E2E_PASSWORD_ADMIN
    BOOKING_E2E_PASSWORD            fallback password for every login

Run them from the repository root, e.g.
    BOOKING_E2E_PASSWORD_ADMIN=... python3 scripts/e2e_rpc/phase0_setup.py
"""
import os
import re
import xmlrpc.client

URL = os.environ.get("BOOKING_E2E_URL", "http://localhost:9071")
DB = os.environ.get("BOOKING_E2E_DB", "odoocalendar")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_config.json")


def password_for(login):
    """Password of `login` for the e2e scripts, read from the environment."""
    key = "BOOKING_E2E_PASSWORD_" + re.sub(r"[^A-Za-z0-9]", "_", login).upper()
    password = os.environ.get(key) or os.environ.get("BOOKING_E2E_PASSWORD")
    if not password:
        raise SystemExit(f"Set {key} (or BOOKING_E2E_PASSWORD) to run the e2e scripts as {login!r}")
    return password


class OdooRPC:
    def __init__(self, login="admin", password=None):
        if password is None:
            password = password_for(login)
        self.url = URL
        self.db = DB
        self.login = login
        self.password = password
        self.common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
        self.models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)
        self.uid = self.common.authenticate(DB, login, password, {})
        if not self.uid:
            raise Exception(f"Authentication failed for {login}")

    def execute(self, model, method, *args, **kwargs):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, list(args), kwargs
        )

    def search(self, model, domain, **kwargs):
        return self.execute(model, 'search', domain, **kwargs)

    def read(self, model, ids, fields=None):
        kw = {}
        if fields:
            kw['fields'] = fields
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'read', [ids], kw
        )

    def search_read(self, model, domain, fields=None, **kwargs):
        kw = dict(kwargs)
        if fields:
            kw['fields'] = fields
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read', [domain], kw
        )

    def create(self, model, vals):
        result = self.execute(model, 'create', [vals])
        if isinstance(result, list):
            return result[0]
        return result

    def write(self, model, ids, vals):
        return self.execute(model, 'write', ids, vals)

    def unlink(self, model, ids):
        return self.execute(model, 'unlink', ids)

    def search_count(self, model, domain):
        return self.execute(model, 'search_count', domain)
