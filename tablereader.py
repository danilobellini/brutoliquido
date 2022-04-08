# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 Danilo de Jesus da Silva Bellini
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, version 3 of the
# License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Created on Mon Jan 27 21:41:26 2014
#
"""
Module for TXT tables reading
"""

from __future__ import unicode_literals
from misc import uopen, currency2float
import math

def line_gen(file_object, comment_symbol="#"):
    """
    Generator for lines (strings) of an input file that aren't empty
    after removing comments that start with the ``comment_symbol``
    and trailing whitespaces.
    """
    for line_raw in file_object.readlines():
        line = line_raw.split(comment_symbol, 1)[0].rstrip()
        if line:
            yield line

def str_to_float(val):
    if "%" in val:
        return currency2float(val.replace("%", "", 1)) * 1e-2
    return currency2float(val)

def read_tables(file_obj, separator_symbol=";"):
    """
    Return a dictionary whose items are the sections of the given file,
    where a section starts by its key (from the first column of a line)
    and whose contents are the following lines
    (starting with at least one whitespace).
    The content lines of a section is a CSV-like table,
    whose header is shared, appearing only before the first section,
    and they're parsed as a list of dicts,
    already converted to floating numbers
    (using "," as the decimal separators, due to the Brazilian locale).
    The "%" suffix means ``1e-2``.
    """
    table = {}
    lines = line_gen(file_obj)
    schema = [el.strip() for el in lines.next().split(separator_symbol)]

    for line in lines:
        if line[0] == " ": # Block continuation
            line_numeric = map(str_to_float, line.split(separator_symbol))
            line_dict = dict(zip(schema, line_numeric))
            table[header].append(line_dict)
        else: # New block
            header = line
            table[header] = []
    return table

def new_processor(*full_schema):

    def halfway_gen(table):
        keys = full_schema[:2]
        start_key, finish_key = keys
        last = None
        for line in sorted(table, key=lambda line: line[start_key]):
            if not last:
                start = line[start_key]
            else:
                start = .5 * (line[start_key] + last[finish_key])
            yield start, {k: v for k, v in line.iteritems() if k not in keys}
            last = line
        yield last[finish_key], None

    def table_gen(table):
        for start, data in sorted(halfway_gen(table)):
            if data:
                if len(full_schema) == 3:
                    yield [start, data[full_schema[2]]]
                elif len(full_schema) > 3:
                    remaining = tuple(data[k] for k in full_schema[2:])
                    yield [start, remaining]
                else:
                    yield [start]
            elif not math.isinf(start):
                yield start

    def reader(table):
        out_table = list(table_gen(table))
        if not isinstance(out_table[-1], list):
            return out_table[:-1], out_table[-1]
        return out_table

    return reader

def load_table(fname, schema):
    result = {}
    proc = new_processor(*schema)
    with uopen(fname, "r") as f:
        for k, table in read_tables(f).iteritems():
            result[k] = proc(table)
    return result
