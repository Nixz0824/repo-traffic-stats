#!/usr/bin/env python3
"""
Archive GitHub traffic (views + clones) for ALL repos of a user/org into one CSV.

Different from archive_traffic.py (single repo): this enumerates every
repository the token can access, fetches each repo's views/clones, and merges
them all into a single `all-traffic.csv`, keyed by (repo, date).

Why a PAT is required:
  The Actions-built-in GITHUB_TOKEN only has access to the single repository
  the workflow runs in. To read traffic across many repositories you need a
  Personal Access Token with the `repo` scope, passed via a secret (env var).

Usage:
    python3 archive_all_traffic.py --all                        # token owner's repos (recommended)
    python3 archive_all_traffic.py --owner Nixz0824              # also include this user's public repos
    python3 archive_all_traffic.py --all --dry-run               # fetch + print, do not write
    python3 archive_all_traffic.py --repo Nixz0824/AiDocks       # just one repo

Env:
    GITHUB_TOKEN / GH_TOKEN / TRAFFIC_PAT   token with `repo` scope
    ALL_TRAFFIC_FILE                        output path (default: all-traffic.csv)

Output CSV columns:
    repo,date,views,uniques,clones,cloners
"""

import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
USER_AGENT = "dsh-traffic-archiver/1.0"
FIELDS = ["repo", "date", "views", "uniques", "clones", "cloners"]
DEFAULT_OUT = "all-traffic.csv"


def get_token():
    return (os.environ.get("TRAFFIC_PAT")
            or os.environ.get("GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN"))


def api_get(path, token, want="json"):
    """GET an endpoint. Returns parsed JSON by default, or the raw response."""
    # `path` may be a bare path (e.g. "/user/repos") OR a full URL (from a
    # pagination Link header). Only prepend the API base for bare paths.
    url = path if path.startswith("http") else API + path
    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    for attempt in (1, 2, 3):
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            if want == "raw":
                return resp
            return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 403 and "Retry-After" in e.headers:
                wait = float(e.headers["Retry-After"])
                print(f"rate limited; sleeping {wait:.0f}s ...", file=sys.stderr)
                time.sleep(wait)
                continue
            if e.code == 403 and attempt < 3:
                print(f"403 on {path}; retrying ...", file=sys.stderr)
                time.sleep(5 * attempt)
                continue
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            # Treat "not found / no access" repos as skippable, not fatal.
            if e.code in (403, 404):
                print(f"  skip (HTTP {e.code}) {path}: {(body or e.reason)[:120]}",
                      file=sys.stderr)
                return None
            sys.exit(f"HTTP {e.code} for {path}: {body or e.reason}")
    return None


def next_link(resp):
    """Return the URL of the next page from a Link header, else None."""
    link = resp.headers.get("Link")
    if not link:
        return None
    for part in link.split(","):
        m = re.search(r'<(.*?)>;\s*rel="next"', part.strip())
        if m:
            return m.group(1)
    return None


def list_repos(token, owner=None):
    """Return [full_name] of repos. owner=None => the token owner's repos."""
    repos = []
    if owner:
        url = f"{API}/users/{owner}/repos?per_page=100&type=all"
    else:
        url = f"{API}/user/repos?per_page=100&type=all"
    while url:
        resp = api_get(url, token, want="raw")
        if resp is None:
            break
        arr = json.load(resp)
        repos.extend(item["full_name"] for item in arr)
        url = next_link(resp)
    return repos


def fetch_day_map(kind, repo, token):
    """{date: {kind: count, kind_uniques: unique}} or {} when skipped."""
    payload = api_get(f"/repos/{repo}/traffic/{kind}", token)
    if payload is None:
        return {}
    day_map = {}
    for row in payload.get(kind, []):
        day = row["timestamp"][:10]
        day_map[day] = {kind: row["count"], kind + "_uniques": row["uniques"]}
    return day_map


def load_existing(path):
    rows = {}
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rows[(row["repo"], row["date"])] = row
    return rows


def main():
    args = sys.argv[1:]
    token = get_token()
    if not token:
        sys.exit("No token set. Provide TRAFFIC_PAT / GITHUB_TOKEN / GH_TOKEN "
                 "(a PAT with `repo` scope is required to read other repos' traffic).")
    dry_run = "--dry-run" in args
    out = os.environ.get("ALL_TRAFFIC_FILE", DEFAULT_OUT)

    single = _arg_value("--repo", args)
    owners = _arg_values("--owner", args)

    if single:
        repos = [single]
    else:
        repos = list_repos(token) if not owners else []
        seen = set(repos)
        for o in owners:
            for full in list_repos(token, owner=o):
                if full not in seen:
                    repos.append(full)
                    seen.add(full)
    if not repos:
        sys.exit("No repositories found. Double-check the token scope/ownership.")

    print(f"archiving {len(repos)} repos ...")
    newest = {}
    for i, full in enumerate(repos, 1):
        day_map = {}
        for kind in ("views", "clones"):
            for day, rec in fetch_day_map(kind, full, token).items():
                day_map.setdefault(day, {}).update(rec)
        for day, rec in day_map.items():
            slot = newest.setdefault((full, day), {})
            for key, out_key in (("views", "views"),
                                 ("views_uniques", "uniques"),
                                 ("clones", "clones"),
                                 ("clones_uniques", "cloners")):
                if key in rec:
                    slot[out_key] = max(slot.get(out_key, 0), rec[key])
        if i % 10 == 0:
            print(f"  ... {i}/{len(repos)} repos done", flush=True)
        time.sleep(1)  # be gentle with the secondary rate limit

    # Merge with existing archive (GitHub revises upward over time).
    rows = load_existing(out)
    for (full, day), rec in newest.items():
        base = rows.setdefault((full, day), {"repo": full, "date": day})
        for field in ("views", "uniques", "clones", "cloners"):
            base[field] = max(int(base.get(field, 0) or 0), int(rec.get(field, 0) or 0))

    ordered = [rows[k] for k in sorted(rows)]
    if not dry_run:
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(ordered)

    # Print a small per-repo summary table of what just got fetched.
    print(f"\nlatest window (repo | date | views | clones):")
    per_repo = {}
    for (full, day), rec in newest.items():
        per_repo.setdefault(full, []).append((day, rec))
    for full in sorted(per_repo):
        items = sorted(per_repo[full])
        last = items[-1]
        day, rec = last
        print(f"  {full:<40} {day}  views={rec.get('views', 0):>4} "
              f"clones={rec.get('clones', 0):>3}")
    print(f"\ntotal archived rows: {len(ordered)}"
          + ("  (dry-run, nothing written)" if dry_run else ""))


def _arg_values(name, args):
    out = []
    for i, a in enumerate(args):
        if a == name and i + 1 < len(args):
            out.append(args[i + 1])
    return out


def _arg_value(name, args):
    vals = _arg_values(name, args)
    return vals[0] if vals else None


if __name__ == "__main__":
    main()
