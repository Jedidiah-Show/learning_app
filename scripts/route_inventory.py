#!/usr/bin/env python3
from app import create_app

app = create_app({'TESTING': True})
routes = []
for rule in app.url_map.iter_rules():
    methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
    routes.append((rule.rule, rule.endpoint, methods))
routes.sort()
for rule, endpoint, methods in routes:
    print(f"{rule}\t{endpoint}\t{','.join(methods)}")
