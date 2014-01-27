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
Miscellanous functions
"""

import codecs

uopen = lambda fname, mode: codecs.open(fname, mode, encoding="utf-8")

def currency2float(val, currency="R$"):
    """ Casts the val string to a float in the given currency """
    val = val.strip().replace(" ", "")
    if val.startswith(currency):
        val = val[2:].lstrip()
    if "." in val and "," in val:
        val = val.replace(min(".,", key=val.index), "")
    if "," in val:
        val = val.replace(",", ".")
    if val.count(".") > 1:
        idx = val.index(".")
        val = ".".join(val[:idx], val[idx + 1:].replace(".", ""))
    if not val:
        return 0.
    return float(val)
