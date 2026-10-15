"""Página imprimível para exportar uma correção do histórico como PDF."""

from flask import render_template_string
from markupsafe import Markup, escape


HTML_PDF_HISTORICO = """
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ item.titulo }} - Correção</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="https://fonts.googleapis.com/css2?family=Lora:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    *{box-sizing:border-box}body{margin:0;background:#f0efe8;color:#29283a;font-family:'DM Sans',sans-serif}
    .sheet{max-width:1120px;margin:24px auto;background:#f7f6f1;border:1px solid #e2e0d8;border-radius:16px;overflow:hidden}
    .heading{padding:20px 24px;background:#fff;border-bottom:1px solid #e2e0d8;display:flex;justify-content:space-between;align-items:center;gap:16px}
    h1{font:600 25px 'Lora',serif;color:#26215c;margin:0}.meta{font-size:12px;color:#888780;margin-top:6px}
    .body-grid{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:16px;padding:18px}
    .panel{background:#fff;border:1px solid #e2e0d8;border-radius:14px;padding:18px;margin-bottom:12px}
    .panel h2{font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin:0 0 14px}
    .essay{font:16px/1.85 'Lora',serif;white-space:pre-wrap;color:#3b3a37}
    .score{background:#26215c;color:#fff;border-radius:15px;padding:20px;margin-bottom:12px;break-inside:avoid}
    .score small{font-size:10px;letter-spacing:1px;text-transform:uppercase;color:#cecbf6}.score strong{display:block;font:600 58px/1 'Lora',serif;margin:6px 0}
    .badge-level{display:inline-block;border:1px solid #ffffff44;background:#ffffff1f;border-radius:20px;padding:4px 12px;font-size:12px}
    .chart{height:190px;display:flex;align-items:flex-end;justify-content:space-around;gap:12px}.column{flex:1;text-align:center;font-size:10px;color:#777}
    .track{height:128px;background:#f0efe8;border-radius:9px;display:flex;align-items:flex-end;overflow:hidden}.fill{width:100%;background:#1d9e75;border-radius:9px 9px 0 0}
    .bar-score{font-weight:700;font-size:12px;color:#333;margin:5px 0 2px}.feedback{padding:11px 0;border-bottom:1px solid #f0efe8;break-inside:avoid}.feedback:last-child{border:0}
    .feedback b{display:block;color:#534ab7;font-size:10px;letter-spacing:.6px;text-transform:uppercase;margin-bottom:4px}.feedback p{font-size:12px;line-height:1.55;color:#5f5e5a;margin:0}
    mark{background:#ffe08a;border-bottom:2px solid #ba7517;padding:0 2px}
    .toolbar{text-align:right;margin:18px auto;max-width:1120px}
    @media(max-width:800px){.body-grid{grid-template-columns:1fr}.sheet{margin:10px}.heading{align-items:flex-start}.toolbar{margin:10px}}
    @media print{body{background:#fff}.toolbar,.screen-only{display:none!important}.sheet{max-width:none;margin:0;border:0;border-radius:0;overflow:visible}.heading,.panel,.score{-webkit-print-color-adjust:exact;print-color-adjust:exact}.heading{padding:0 0 12px}.body-grid{display:block;padding:12px 0}.panel{padding:14px;break-inside:auto}.panel h2{break-after:avoid}.essay{font-size:13px;orphans:3;widows:3}.score{break-inside:avoid}.chart{break-inside:avoid}.feedback{break-inside:avoid}.feedback p{font-size:10px}@page{size:A4;margin:12mm}}
  </style>
</head>
<body>
  <div class="toolbar"><button class="btn btn-primary" onclick="window.print()">Imprimir / Salvar como PDF</button></div>
  <main class="sheet">
    <header class="heading"><div><h1>{{ item.titulo or 'Redação sem título' }}</h1><div class="meta">{{ item.data_formatada }} · {{ item.genero or 'Gênero não informado' }} · Tema: {{ item.tema or 'Tema livre' }}</div></div><button class="btn btn-outline-primary screen-only" onclick="window.print()" aria-label="Salvar como PDF"><i class="bi bi-download"></i> PDF</button></header>
    <div class="body-grid">
      <section class="panel"><h2>Redação enviada</h2><div class="essay">{{ item.conteudo_destacado }}</div></section>
      <aside>
        <section class="score"><small>Nota geral</small><strong>{{ '%.1f'|format(item.nota or 0) }}</strong><span class="badge-level">{{ item.nivel }}</span></section>
        <section class="panel"><h2>Notas por critério</h2><div class="chart">{% for criterio in item.criterios %}<div class="column"><div class="track"><div class="fill" style="height:{{ criterio.percentual }}%"></div></div><div class="bar-score">{{ '%.1f'|format(criterio.nota) }}</div>{{ criterio.nome }}</div>{% endfor %}</div></section>
        <section class="panel"><h2>Correções detalhadas</h2>{% for comentario in item.comentarios %}<div class="feedback"><b>{{ comentario.nome }}</b><p>{{ comentario.texto or 'Nenhuma observação salva para este critério.' }}</p>{% for desconto in item.descontos if desconto.criterio|lower == comentario.nome|lower and desconto.problema not in ['Parcela restante da perda não discriminada por erro específico', 'Perda do critério não detalhada em erros individuais'] %}<p><strong>{{ desconto.problema or '' }}</strong> · Desconto: {{ desconto.desconto if desconto.desconto is not none else 'não configurado' }}<br>{{ desconto.justificativa or '' }}</p>{% endfor %}</div>{% endfor %}
        </section>
      </aside>
    </div>
  </main>
  <script>window.addEventListener("load", function () { if (document.fonts && document.fonts.ready) { document.fonts.ready.then(function () { setTimeout(function () { window.print(); }, 150); }); } else { setTimeout(function () { window.print(); }, 150); } });</script>
</body>
</html>
"""


def _marcar_trechos(texto, destaques):
    encontrados = []
    for apontamento in destaques if isinstance(destaques, list) else []:
        trecho = str(apontamento.get("trecho") or "").strip()
        posicao = texto.find(trecho) if trecho else -1
        if posicao >= 0:
            encontrados.append((posicao, posicao + len(trecho), apontamento))

    encontrados.sort(key=lambda item: item[0])
    partes = []
    cursor = 0
    for inicio, fim, apontamento in encontrados:
        if inicio < cursor:
            continue
        partes.append(escape(texto[cursor:inicio]))
        titulo = f"{apontamento.get('criterio') or 'Apontamento'}: {apontamento.get('comentario') or ''}"
        partes.append(Markup('<mark title="{}">{}</mark>').format(escape(titulo), escape(texto[inicio:fim])))
        cursor = fim
    partes.append(escape(texto[cursor:]))
    return Markup("").join(partes)


def gerar_pdf_historico(item):
    feedback = item.get("feedback") or {}
    notas = [
        ("Estrutura", item.get("nEstrutura")),
        ("Tema", item.get("nTema")),
        ("Gramática", item.get("nGramatica")),
        ("Repertório", item.get("nRepertorio")),
        ("Coesão", item.get("nCoesao")),
    ]
    item["criterios"] = [
        {"nome": nome, "nota": float(nota or 0), "percentual": max(0, min(100, float(nota or 0) * 10))}
        for nome, nota in notas
    ]
    item["comentarios"] = [
        {"nome": nome, "texto": feedback.get(chave)}
        for nome, chave in [
            ("Estrutura", "txtStruct"), ("Tema", "txtTema"),
            ("Gramática", "txtGeC"), ("Repertório", "txtRep"),
            ("Coesão textual", "txtCoe"), ("Recomendações", "txtTip")
        ]
    ]
    item["descontos"] = feedback.get("detalhes_descontos") or []
    item["conteudo_destacado"] = _marcar_trechos(
        item.get("conteudo") or "", feedback.get("highlights") or []
    )
    return render_template_string(HTML_PDF_HISTORICO, item=item)
