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
import coffeescript, codecs
from os.path import exists, getmtime
import os

app = Flask(__name__)
app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')


uopen = lambda fname, mode: codecs.open(fname, mode, encoding="utf-8")

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


# Pares tabela, limite para cálculo de alíquota
# Tabela com o piso (bruto) associado à alíquota
inss_pares = DateStrKeyDict({
    "2011-01": ([
        [   0.000, .08],
        [1106.905, .09],
        [1844.835, .11],
    ], 3689.66),
    "2011-07": ([
        [   0.000, .08],
        [1107.525, .09],
        [1845.875, .11],
    ], 3691.74),
    "2012": ([
        [   0.000, .08],
        [1174.865, .09],
        [1958.105, .11],
    ], 3916.20),
    "2013": ([
        [   0.000, .08],
        [1247.705, .09],
        [2079.505, .11],
    ], 4159.00),
    "2014": ([
        [   0.000, .08],
        [1317.075, .09],
        [2195.125, .11],
    ], 4390.24),
})

inss_teto = DateStrKeyDict((k, round(limite * tabela[-1][-1], 2)) # Em R$
                           for k, (tabela, limite) in inss_pares.iteritems())
inss_tabela = DateStrKeyDict((k, tabela)
                              for k, (tabela, lim) in inss_pares.iteritems())

# Piso (bruto - INSS) associado ao par (alíquota, valor a deduzir)
irpf_tabela = DateStrKeyDict({
    "2011-01": [
        [1499.155, (.075, 112.43)],
        [2246.755, (.15,  280.94)],
        [2995.705, (.225, 505.62)],
        [3743.195, (.275, 692.78)],
    ],
    "2011-04": [
        [1566.615, (.075, 117.49)],
        [2347.855, (.15,  293.58)],
        [3130.515, (.225, 528.37)],
        [3911.635, (.275, 723.95)],
    ],
    "2012": [
        [1637.115, (.075, 122.78)],
        [2453.505, (.15,  306.80)],
        [3271.385, (.225, 552.15)],
        [4087.655, (.275, 756.53)],
    ],
    "2013": [
        [1710.785, (.075, 128.31)],
        [2563.915, (.15,  320.60)],
        [3418.595, (.225, 577.00)],
        [4271.595, (.275, 790.58)],
    ],
    "2014": [
        [1787.775, (.075, 134.08)],
        [2679.295, (.15,  335.03)],
        [3572.435, (.225, 602.96)],
        [4463.815, (.275, 826.15)],
    ],
})

datas_base = sorted(set(irpf_tabela).union(set(inss_tabela)))
datas_base_dict = DateStrKeyDict((k, None) for k in datas_base)


def obtem_valores_tabela(bruto, tabela):
    first = tabela[0][1]
    start = 0. if isinstance(first, Number) else tuple(0. for el in first)
    return reduce(lambda val, (piso, novo_val):
                      novo_val if bruto >= piso else val,
                  tabela, start)

def inss(bruto):
    inss_aliq = obtem_valores_tabela(bruto, inss_tabela[g.data])
    return min(bruto * inss_aliq, inss_teto[g.data])

def bruto_sem_inss2liquido(bruto):
    irpf_aliq, irpf_deduzir = obtem_valores_tabela(bruto, irpf_tabela[g.data])
    return bruto * (1 - irpf_aliq) + irpf_deduzir

def liquido2bruto_sem_inss(liq):
    func = lambda bruto: bruto_sem_inss2liquido(bruto) - liq
    return findroot(func, liq)

def bruto_sem_inss2bruto(bruto_sem_inss):
    func = lambda bruto: bruto - bruto_sem_inss - inss(bruto)
    return findroot(func, bruto_sem_inss)


def str2r(val):
    """ Trata a string e converte para ponto flutuante o valor em R$ """
    val = val.strip().replace(" ", "")
    if val.startswith("R$"):
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


def todos_valores(bruto):
    """ Cálculo direto do IRPF, INSS e salário líquido a partir do bruto """
    valor_inss = inss(bruto)
    bruto_sem_inss = round(bruto - valor_inss, 2)
    liquido = round(bruto_sem_inss2liquido(bruto_sem_inss), 2)
    ir_aliq, ir_deduzir = obtem_valores_tabela(bruto, irpf_tabela[g.data])
    return dict(
        bruto = bruto,
        bruto_sem_inss = bruto_sem_inss,
        liquido = liquido,
        inss = round(valor_inss, 2),
        inss_aliq = obtem_valores_tabela(bruto, inss_tabela[g.data]),
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
        valores = [str2r(source.get(k, ""))
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
