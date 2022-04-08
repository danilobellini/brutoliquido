#!/usr/bin/env python
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
# Created on Wed Jan 08 20:03:18 2014
#
"""
Conversor bidirecional de valores de salário bruto e líquido
"""

from __future__ import unicode_literals, division
from datetime import datetime
from numbers import Number
from mpmath import findroot
from flask import Flask, jsonify, render_template, request, g, abort
import coffeescript
from os.path import exists, getmtime
import os

from misc import uopen, currency2float
from tablereader import load_table

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')


def static_file_converted(fnamebase, converter, from_ext, to_ext):
    in_fname = "templates/{fnamebase}.{from_ext}".format(**locals())
    out_fname_nodir = "{fnamebase}.{to_ext}".format(**locals())
    out_fname = os.path.join(app.static_folder, out_fname_nodir)

    if not exists(in_fname):
        abort(404)

    if (not exists(out_fname)) or getmtime(in_fname) >= getmtime(out_fname):
        if not exists(app.static_folder):
            os.makedirs(app.static_folder)
        with uopen(in_fname,  "r") as in_file:
            with uopen(out_fname, "w") as out_file:
                out_file.write(converter(in_file.read()))

    return out_fname_nodir

@app.route(app.static_url_path + "/<path:fnamebase>.js")
def _get_js(fnamebase):
    return app.send_static_file(static_file_converted(
      fnamebase = fnamebase,
      converter = coffeescript.compile,
      from_ext = "coffee",
      to_ext = "js"
    ))


class DateStrKeyDict(dict):
    """ Dicionário em que as chaves são strings representando datas """
    def encontra_data_base(self, data=None):
        if data in self:
            return data
        if data is None:
            data = datetime.now().isoformat()
        return max(key for key in self.keys() if key < data)

    def __missing__(self, data):
        resultado = self[self.encontra_data_base(data)]
        if data is None:
            self[None] = resultado
        return resultado


def load_txt(fname):
    return DateStrKeyDict(
        load_table(os.path.join(app.static_folder, fname),
                   ["Inicial", "Final", "Alíquota", "Valor a deduzir"])
    )


# Pares tabela, limite para cálculo de alíquota
# Tabela com o piso (bruto) associado à alíquota
inss_pares = load_txt("inss.txt")
inss_teto = DateStrKeyDict(  # Em R$
    (data_str, round(limite * tabela[-1][-1][0] - tabela[-1][-1][1], 2))
    for data_str, (tabela, limite) in inss_pares.iteritems()
)
inss_tabela = DateStrKeyDict((k, tabela)
                              for k, (tabela, lim) in inss_pares.iteritems())

# Piso (bruto - INSS) associado ao par (alíquota, valor a deduzir)
irpf_tabela = load_txt("irpf.txt")

datas_base = sorted(set(irpf_tabela).union(set(inss_tabela)))
datas_base_dict = DateStrKeyDict((k, None) for k in datas_base)


def obtem_valores_tabela(bruto, tabela):
    start = tuple(0. for el in tabela[0][1])
    return reduce(lambda val, (piso, novo_val):
                      novo_val if bruto >= piso else val,
                  tabela, start)

def inss(bruto):
    inss_aliq, inss_deduzir = obtem_valores_tabela(bruto, inss_tabela[g.data])
    return min(bruto * inss_aliq - inss_deduzir, inss_teto[g.data])

def bruto_sem_inss2liquido(bruto):
    irpf_aliq, irpf_deduzir = obtem_valores_tabela(bruto, irpf_tabela[g.data])
    return bruto * (1 - irpf_aliq) + irpf_deduzir

def liquido2bruto_sem_inss(liq):
    func = lambda bruto: bruto_sem_inss2liquido(bruto) - liq
    return findroot(func, liq)

def bruto_sem_inss2bruto(bruto_sem_inss):
    func = lambda bruto: bruto - bruto_sem_inss - inss(bruto)
    return findroot(func, bruto_sem_inss)


def todos_valores(bruto):
    """ Cálculo direto do IRPF, INSS e salário líquido a partir do bruto """
    valor_inss = inss(bruto)
    bruto_sem_inss = round(bruto - valor_inss, 2)
    liquido = round(bruto_sem_inss2liquido(bruto_sem_inss), 2)
    ir_aliq, ir_deduzir = obtem_valores_tabela(bruto, irpf_tabela[g.data])
    inss_aliq, inss_deduzir = obtem_valores_tabela(bruto, inss_tabela[g.data])
    return dict(
        bruto = bruto,
        bruto_sem_inss = bruto_sem_inss,
        liquido = liquido,
        inss = round(valor_inss, 2),
        inss_aliq=inss_aliq,
        inss_deduzir=inss_deduzir,
        ir = round(bruto_sem_inss - liquido, 2),
        ir_aliq = ir_aliq,
        ir_deduzir = ir_deduzir,
    )


@app.route("/")
def index():
    return render_template("index.jade", datas_base=datas_base)


def error_json(msg):
    return jsonify(status="oops", err_msg=msg)


@app.route("/calc", methods=["GET", "POST"])
def ajax_calc():
    # Tratamento dos valores de entrada
    source = request.args if request.method == "GET" else request.form
    g.data = datas_base_dict.encontra_data_base(source.get("data", None))
    try:
        valores = [currency2float(source.get(k, ""))
                   for k in ["liquido", "bruto", "bruto_sem_inss"]]
    except ValueError:
        return error_json("Valor numérico fornecido não reconhecido")
    if len(filter(bool, valores)) > 1:
        return error_json("Use apenas um entre liquido, bruto ou "
                          "bruto_sem_inss")

    # Obtém o valor bruto
    liquido, bruto, bruto_sem_inss = valores
    if liquido:
        bruto_sem_inss = round(liquido2bruto_sem_inss(liquido), 2)
    if liquido or bruto_sem_inss:
        bruto = bruto_sem_inss2bruto(bruto_sem_inss)

    # Resultado
    result = todos_valores(round(bruto, 2))
    result["status"] = "ok"
    result["data_base"] = g.data
    return jsonify(**result)


if __name__ == "__main__":
    app.run(debug=True)
