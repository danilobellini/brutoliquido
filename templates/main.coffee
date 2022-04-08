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
# Created on Wed Jan 13 14:35:56 2014
#
###
Tratamento de eventos e AJAX do conversor bruto/líquido
###

# Event handler binding helper function
addEvent = if document.addEventListener \
  then (obj, name, callback) -> obj.addEventListener name, callback \
  else (obj, name, callback) -> obj.attachEvent "on#{name}", callback

# Escaped and serialized form data string from an Object
formString = (obj) -> ([k, v].map(escape).join "=" for k, v of obj).join "&"

# Convert all HTTPInputElement inputs into one Object
fieldsToObject = (args...) ->
  msg = {}
  msg["#{field.name}"] = field.value for field in args
  return msg

# Initialization
[last_field, data_field, result] = (document.getElementById el \
                                    for el in ["bruto", "data", "result"])

# Refresh contents via an AJAX call
refresh = ->
  xhr = new window.XMLHttpRequest()
  xhr.onload = (evt) ->
    result.textContent = @responseText.replaceAll(",", ",\n ")
  xhr.open "POST", "/calc", true # method, address, async
  xhr.setRequestHeader "Content-Type", "application/x-www-form-urlencoded"
  xhr.send formString fieldsToObject data_field, last_field

# Input changed handler
changeObj = ->
  if @value.trim()
    last_field = @
    refresh()

# Binds an event handler for every value changed
for el in document.getElementsByClassName "bl"
  addEvent el, evt, changeObj for evt in ["input", "propertychange"]
addEvent data_field, "change", refresh
