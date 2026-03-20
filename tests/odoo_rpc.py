"""
Odoo XML-RPC helper for testing.
"""
import xmlrpc.client

URL = "http://localhost:9071"
DB = "odoocalendar"

class OdooRPC:
    def __init__(self, login="admin", password="admin"):
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
