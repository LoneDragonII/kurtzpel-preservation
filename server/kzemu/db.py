# SPDX-License-Identifier: AGPL-3.0-or-later
"""SQLite persistence: accounts (keyed by SteamID64) and characters."""
import sqlite3, time

SCHEMA = """
CREATE TABLE IF NOT EXISTS account (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    steam_id TEXT UNIQUE NOT NULL,
    created INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS character (
    uid INTEGER PRIMARY KEY AUTOINCREMENT,
    account_uid INTEGER NOT NULL REFERENCES account(uid),
    name TEXT NOT NULL,
    appearance BLOB,           -- raw optional struct bytes as the client sent them
    look BLOB,
    create_req BLOB,           -- the whole CREATE_CHARACTER_REQ payload, kept for later decoding
    created INTEGER NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0
);
"""


class DB:
    def __init__(self, path):
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.executescript(SCHEMA)
        # start character uids away from 0 so they never look like "no character"
        if not self.c.execute("SELECT 1 FROM sqlite_sequence WHERE name='character'").fetchone():
            self.c.execute("INSERT INTO sqlite_sequence(name, seq) VALUES ('character', 1000)")
        self.c.commit()

    def account(self, steam_id: str) -> int:
        r = self.c.execute('SELECT uid FROM account WHERE steam_id=?', (steam_id,)).fetchone()
        if r: return r['uid']
        cur = self.c.execute('INSERT INTO account(steam_id, created) VALUES (?, ?)', (steam_id, int(time.time())))
        self.c.commit()
        return cur.lastrowid

    def characters(self, account_uid: int):
        rows = self.c.execute('SELECT * FROM character WHERE account_uid=? AND deleted=0 ORDER BY uid', (account_uid,))
        return [dict(r) for r in rows]

    def character(self, account_uid: int, uid: int):
        r = self.c.execute('SELECT * FROM character WHERE account_uid=? AND uid=? AND deleted=0', (account_uid, uid)).fetchone()
        return dict(r) if r else None

    def create_character(self, account_uid, name, appearance=None, look=None, create_req=None):
        cur = self.c.execute('INSERT INTO character(account_uid, name, appearance, look, create_req, created) VALUES (?,?,?,?,?,?)',
                             (account_uid, name, appearance, look, create_req, int(time.time())))
        self.c.commit()
        return self.character(account_uid, cur.lastrowid)

    def delete_character(self, account_uid, uid):
        self.c.execute('UPDATE character SET deleted=1 WHERE account_uid=? AND uid=?', (account_uid, uid))
        self.c.commit()
