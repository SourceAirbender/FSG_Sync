# -*- coding: utf-8 -*-
#
# Copyright © 2022 Jean Michault

# License: GPL-3.0-or-later
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional


def _tzinfo_from_zone(zone: str):
    """Return tzinfo for 'Z' or ±HH[:MM]."""
    if not zone or zone == "Z":
        return timezone.utc
    # Accept +HH or +HH:MM (and negatives)
    sign = 1
    s = zone.strip()
    if s[0] == "-":
        sign = -1
        s = s[1:]
    elif s[0] == "+":
        s = s[1:]
    parts = s.split(":")
    try:
        hours = int(parts[0]) if parts and parts[0] else 0
        minutes = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return timezone.utc
    return timezone(timedelta(hours=sign * hours, minutes=sign * minutes))


class SimpleDate:
    """
    ISO 8601 extended 'formal' date subset:
    ±YYYY[-MM[-DD[Thh[:mm[:ss]][±hh[:mm]|Z]]]]

    Attributes:
        year, month, day, hour, minute (ints)
        second (float)
        zone (str)  -> 'Z' or ±HH[:MM]
    """

    def __init__(self, value: Optional[str] = None):
        # defaults
        self.year = self.month = self.day = self.hour = self.minute = 0
        self.second = 0.0
        self.zone = "Z"
        if not value:
            return
        if len(value) < 2:
            print("invalid formal date: " + value)
            return

        # timezone Z?
        if "Z" in value:
            value = value.replace("Z", "")
            self.zone = "Z"

        # split date/time
        parts_t = value.split("T")
        date_part = parts_t[0]
        if len(date_part) < 2:
            print("invalid formal date: " + value)
            return

        # allow explicit '+'
        if date_part[0] == "+":
            date_part = date_part[1:]

        # sign handling for negative years
        if date_part and date_part[0] == "-":
            chunks = date_part[1:].split("-")
            sign = -1
        else:
            chunks = date_part.split("-")
            sign = 1

        if not chunks or not (chunks[0] and (chunks[0][0] in "+-" or chunks[0][0].isdigit())):
            return

        if chunks[0] != "":
            self.year = sign * int(chunks[0])
        if len(chunks) > 1 and chunks[1] != "":
            self.month = int(chunks[1])
        if len(chunks) > 2 and chunks[2] != "":
            self.day = int(chunks[2])

        # parse time + zone
        if len(parts_t) > 1:
            time_part = parts_t[1]  # hh[:mm[:ss]][±hh[:mm]]
            # find first + or - as zone separator (not at position 0 unless hour is missing)
            pos_plus = time_part.find("+")
            pos_minus = time_part.find("-")
            pos_sign = -1
            if pos_plus >= 0 and pos_minus >= 0:
                pos_sign = min(pos_plus, pos_minus)
            else:
                pos_sign = max(pos_plus, pos_minus)

            if pos_sign >= 0:
                self.zone = time_part[pos_sign:]
                time_part = time_part[:pos_sign]

            tchunks = time_part.split(":")
            if tchunks and tchunks[0] != "":
                self.hour = int(tchunks[0])
            if len(tchunks) > 1 and tchunks[1] != "":
                self.minute = int(tchunks[1])
            if len(tchunks) > 2 and tchunks[2] != "":
                try:
                    self.second = float(tchunks[2])
                except ValueError:
                    # tolerate 'ss' without decimals
                    self.second = float(int(tchunks[2]))

    def __str__(self) -> str:
        # ±YYYY[-MM[-DD[Thh[:mm[:ss]][±hh[:mm]|Z]]]]
        if self.year == 0:
            return ""
        res = "+" if self.year >= 0 else ""
        res += f"{self.year:04d}"
        if self.month:
            res += f"-{self.month:02d}"
            if self.day:
                res += f"-{self.day:02d}"
        if self.hour:
            res += f"T{self.hour:02d}"
            if self.minute:
                res += f":{self.minute:02d}"
                if self.second:
                    # keep integer formatting if .0
                    if abs(self.second - int(self.second)) < 1e-9:
                        res += f":{int(self.second):02d}"
                    else:
                        res += f":{self.second:02f}".rstrip("0").rstrip(".")
            res += self.zone
        return res

    def datetime(self) -> datetime:
        """Return a Python datetime (uses minimal valid month/day when missing)."""
        # month/day must be >= 1 for datetime(); keep behavior permissive
        month = self.month or 1
        day = self.day or 1
        tz = _tzinfo_from_zone(self.zone)
        micro = round((self.second % 1) * 1_000_000)
        return datetime(self.year, month, day, self.hour, self.minute, int(self.second), microsecond=micro, tzinfo=tz)

    def int(self) -> int:
        """Epoch milliseconds."""
        return round(self.datetime().timestamp() * 1000)


class DateFormal:
    """
    Formal date with optional approximation, repetition count, and range/duration.

    Fields:
        approximate (bool)         # 'A' prefix
        is_range (bool)            # presence of a second component
        occurrences (int)          # 'R{n}/' prefix
        start_date (SimpleDate)
        end_date (SimpleDate)
        duration (str | None)      # ISO 8601 duration like 'PnnYnnMnnDTnnHnnMnnS'
    """

    def __init__(self, src: Optional[str] = None):
        self.approximate = False
        self.is_range = False
        self.occurrences = 0
        self.start_date = SimpleDate()
        self.end_date = SimpleDate()
        self.duration: Optional[str] = None
        self.parse(src)

    def parse(self, src: Optional[str]) -> None:
        if not src or len(src) < 5:
            return

        s = src
        if s[0] == "A":
            self.approximate = True
            s = s[1:]

        if s and s[0] == "R":
            s = s[1:]
            parts = s.split("/", 1)
            self.occurrences = int(parts[0]) or 1
            s = parts[1] if len(parts) > 1 else ""

        parts = s.split("/")
        self.start_date = SimpleDate(parts[0])
        self.is_range = len(parts) > 1

        if self.is_range and len(parts) > 1 and len(parts[1]) > 1:
            # duration if second part starts with 'P', otherwise an end date
            if parts[1].startswith("P"):
                self.duration = parts[1]
            else:
                self.end_date = SimpleDate(parts[1])

    def to_string(self) -> str:
        return str(self)

    def __str__(self) -> str:
        # 'A' + 'R{n}/' + start + ('/' + end|duration)
        res = "A" if self.approximate else ""
        if self.occurrences > 0:
            res += f"R{self.occurrences}/"
        res += str(self.start_date)
        if self.is_range:
            res += "/"
            if self.duration:
                res += self.duration
            elif self.end_date:
                res += str(self.end_date)
        return res
