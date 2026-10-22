#!/usr/bin/env python3
"""Exercise both dashboards against a real, DISPOSABLE MariaDB database.

This suite writes/prunes sensor rows. Never point it at production data.
Only Python's standard library is required.
"""
import argparse
import json
import os
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request


class GatewayContract(unittest.TestCase):
    base_url = ""
    paths = ()
    api_key = ""

    def setUp(self):
        self.created = []
        self.owner = int(time.time_ns() % 1_000_000_000) + 1

    def tearDown(self):
        for app, record_id in self.created:
            self.call(app, "delete", {"Id": record_id}, allowed=(200, 404))

    def call(self, app, action=None, fields=None, *, method="POST", key=True,
             allowed=(200,), raw_query=None):
        params = {} if action is None else {"action": action}
        url = self.base_url.rstrip("/") + app.rstrip("/") + "/AjaxIoT.php"
        if raw_query is not None:
            url += "?" + raw_query
        else:
            url += "?" + urllib.parse.urlencode(params)
        data = urllib.parse.urlencode(fields or {}).encode()
        headers = {}
        if key is not False:
            headers["X-API-Key"] = self.api_key if key is True else key
        if method == "GET":
            url += "&" + data.decode()
            data = None
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            body = response.read().decode("utf-8")
        self.assertIn(status, allowed, f"{app} {action}: HTTP {status}: {body}")
        self.assertTrue(content_type.startswith("application/json"), content_type)
        result = json.loads(body)  # PHP warnings/fatals must never pollute JSON.
        self.assertNotIn("Debug", result)
        self.assertEqual(result["Result"], "OK" if status == 200 else "ERROR")
        return result

    def create(self, app, **changes):
        fields = {"KeyName": "test", "Data": "12.5", "OwnerId": self.owner,
                  "Datatype": "1", "IoTProjectsId": 703}
        fields.update(changes)
        result = self.call(app, "create", fields)
        record = result["Record"]
        self.assertGreater(int(record["Id"]), 0)
        self.created.append((app, record["Id"]))
        return record

    def rows(self, app):
        result = self.call(app, "list", method="GET", key=False)
        self.assertEqual(int(result["TotalRecordCount"]), len(result["Records"]))
        return result["Records"]

    def test_dashboards_load(self):
        for app in self.paths:
            for page in ("index.php",):
                with self.subTest(app=app, page=page):
                    url = self.base_url.rstrip("/") + app.rstrip("/") + "/" + page
                    with urllib.request.urlopen(url, timeout=10) as response:
                        self.assertEqual(response.status, 200)
                        body = response.read().decode()
                    self.assertIn("chart_div", body)
                    self.assertNotIn("Fatal error", body)
                    self.assertNotIn(self.api_key, body)

    def test_read_contract(self):
        for app in self.paths:
            with self.subTest(app=app):
                self.rows(app)
                self.call(app, "list", key=False)  # Existing dashboard uses POST.

    def test_unknown_and_missing_action(self):
        for app in self.paths:
            with self.subTest(app=app):
                self.call(app, None, allowed=(400,))
                self.call(app, "unknown", allowed=(400,))
                self.call(app, raw_query="action[]=list", allowed=(400,))

    def test_all_mutations_require_key(self):
        for app in self.paths:
            for action in ("create", "update", "delete", "insert", "insertByAPIKey"):
                for key in (False, "incorrect-test-key"):
                    with self.subTest(app=app, action=action, key=bool(key)):
                        self.call(app, action, key=key, allowed=(403,))

    def test_create_returns_actual_new_record(self):
        for app in self.paths:
            with self.subTest(app=app):
                first = self.create(app, Data="1")
                second = self.create(app, Data="2")
                self.assertGreater(int(second["Id"]), int(first["Id"]))
                self.assertEqual(str(second["Data"]), "2")
                self.assertTrue(any(int(r["Id"]) == int(second["Id"]) for r in self.rows(app)))

    def test_quoted_and_unicode_values_remain_data(self):
        for app in self.paths:
            with self.subTest(app=app):
                value = "27.5'); DROP TABLE IoTTable; --"
                record = self.create(app, KeyName="溫度'計", Data=value)
                self.assertEqual(record["KeyName"], "溫度'計")
                self.assertEqual(record["Data"], value)
                self.assertTrue(self.rows(app))

    def test_create_legacy_optional_key_name(self):
        for app in self.paths:
            with self.subTest(app=app):
                result = self.call(app, "create", {"Data": "3", "OwnerId": self.owner,
                    "Datatype": "1", "IoTProjectsId": 703})
                self.created.append((app, result["Record"]["Id"]))
                self.assertEqual(result["Record"]["KeyName"], "")

    def test_update_owner_independent_of_datatype(self):
        for app in self.paths:
            with self.subTest(app=app):
                record = self.create(app)
                fields = {"Id": record["Id"], "Data": "-2.75", "OwnerId": self.owner + 1,
                    "Datatype": "7", "IoTProjectsId": 704, "Datetime": "2026-10-22 12:34:56"}
                self.call(app, "update", fields)
                updated = next(r for r in self.rows(app) if int(r["Id"]) == int(record["Id"]))
                self.assertEqual(int(updated["OwnerId"]), self.owner + 1)
                self.assertEqual(str(updated["Datatype"]), "7")
                self.assertEqual(str(updated["Data"]), "-2.75")
                self.assertEqual(updated["Datetime"], fields["Datetime"])
                self.call(app, "update", fields)  # Idempotent updates must not become 404.

    def test_delete_and_not_found(self):
        for app in self.paths:
            with self.subTest(app=app):
                record = self.create(app)
                self.call(app, "delete", {"Id": record["Id"]})
                self.call(app, "delete", {"Id": record["Id"]}, allowed=(404,))
                self.assertFalse(any(int(r["Id"]) == int(record["Id"]) for r in self.rows(app)))

    def test_invalid_fields_rejected_without_writes(self):
        for app in self.paths:
            with self.subTest(app=app):
                before = len(self.rows(app))
                base = {"KeyName": "test", "Data": "1", "OwnerId": self.owner,
                        "Datatype": "1", "IoTProjectsId": 703}
                for field, value in (("OwnerId", "0 OR 1=1"), ("OwnerId", "1.5"),
                                     ("IoTProjectsId", "99999999999999999"),
                                     ("Data", "X" * 51), ("KeyName", "Y" * 51)):
                    self.call(app, "create", dict(base, **{field: value}), allowed=(400,))
                self.call(app, "create", {}, allowed=(400,))
                self.call(app, "delete", {"Id[]": "1"}, allowed=(400,))
                self.call(app, "delete", {"Id": "1 OR 1=1"}, allowed=(400,))
                self.assertEqual(len(self.rows(app)), before)

    def test_insert_get_and_legacy_api_key_parameter(self):
        for app in self.paths:
            with self.subTest(app=app):
                fields = {"KeyName": "x", "Data": "42", "Datatype": "1", "APIKey": self.api_key}
                inserted = self.call(app, "insertByAPIKey", fields, key=False, method="GET")
                self.created.append((app, inserted["Record"]["Id"]))
                self.assertTrue(any(r["KeyName"] == "x" and str(r["Data"]) == "42"
                                    and int(r["OwnerId"]) == 0 for r in self.rows(app)))
                inserted = self.call(app, "insert", {"KeyName": "legacy", "Data": "9", "OwnerId": self.owner,
                    "Datatype": "1", "IoTProjectsId": 703}, method="GET")
                matches = [r for r in self.rows(app) if int(r["Id"]) == int(inserted["Record"]["Id"])]
                self.assertEqual(len(matches), 1)
                self.created.append((app, matches[0]["Id"]))

    def test_retention_keeps_50_only_in_selected_group(self):
        for app in self.paths:
            with self.subTest(app=app):
                other = self.create(app, IoTProjectsId=704, Data="preserve")
                for number in range(55):
                    self.call(app, "insert", {"KeyName": "retention", "Data": str(number),
                        "OwnerId": self.owner, "Datatype": "1", "IoTProjectsId": 703})
                rows = self.rows(app)
                group = [r for r in rows if int(r["OwnerId"]) == self.owner and int(r["IoTProjectsId"]) == 703]
                self.assertEqual(len(group), 50)
                self.assertEqual(sorted(int(r["Data"]) for r in group), list(range(5, 55)))
                self.assertTrue(any(int(r["Id"]) == int(other["Id"]) for r in rows))
                self.created.extend((app, row["Id"]) for row in group)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--main-path", default="/")
    parser.add_argument("--ces-path", default="/ces/")
    parser.add_argument("--api-key", default=os.environ.get("IOT_API_KEY"))
    parser.add_argument("--disposable-db", action="store_true", help="Confirm database contains no real data")
    args = parser.parse_args()
    if not args.disposable_db or not args.api_key:
        parser.error("--disposable-db and IOT_API_KEY (or --api-key) are required")
    GatewayContract.base_url = args.base_url
    GatewayContract.paths = (args.main_path, args.ces_path)
    GatewayContract.api_key = args.api_key
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GatewayContract)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
