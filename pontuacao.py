"""Concilia os descontos explicados com as notas já atribuídas por critério."""

import unicodedata


CRITERIOS = {
    "estrutura": ("Estrutura", "nota_estrutura"),
    "tema": ("Tema", "nota_tema"),
    "gramatica": ("Gramática", "nota_gramatica"),
    "repertorio": ("Repertório", "nota_repertorio"),
    "coesao": ("Coesão Textual", "nota_coesaoTextual"),
}


def _chave_criterio(valor):
    texto = unicodedata.normalize("NFD", str(valor or "").casefold())
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    if "estrutur" in texto:
        return "estrutura"
    if "tema" in texto:
        return "tema"
    if "gram" in texto or "norma padrao" in texto:
        return "gramatica"
    if "repert" in texto:
        return "repertorio"
    if "coes" in texto:
        return "coesao"
    return None


def normalizar_descontos(detalhes, notas):
    """Faz cada grupo de apontamentos corresponder à perda do seu critério.

    Os descontos não são subtraídos novamente da nota geral. A média das notas
    por critério continua sendo a única fonte da nota geral.
    """
    detalhes = detalhes if isinstance(detalhes, list) else []
    agrupados = {chave: [] for chave in CRITERIOS}
    for item in detalhes:
        if not isinstance(item, dict):
            continue
        chave = _chave_criterio(item.get("criterio"))
        if chave:
            agrupados[chave].append(dict(item, criterio=CRITERIOS[chave][0]))

    resultado = []
    for chave, (nome, chave_nota) in CRITERIOS.items():
        try:
            nota = max(0.0, min(10.0, float(notas.get(chave_nota, 0) or 0)))
        except (TypeError, ValueError):
            nota = 0.0
        perda = round(10.0 - nota, 1)
        itens = agrupados[chave]
        if perda <= 0:
            continue

        valores = []
        for item in itens:
            try:
                valor = max(0.0, float(item.get("desconto") or 0))
            except (TypeError, ValueError):
                valor = 0.0
            valores.append(valor)

        soma = sum(valores)
        if not itens or soma <= 0:
            resultado.append({
                "criterio": nome,
                "problema": "Perda do critério não detalhada em erros individuais",
                "desconto": perda,
                "justificativa": "A nota atribuída implica essa perda em relação ao máximo do critério, mas a IA não a vinculou a apontamentos específicos.",
            })
            continue

        if soma > perda + 0.04:
            ajustados = []
            restante = perda
            for indice, valor in enumerate(valores):
                if indice == len(valores) - 1:
                    parte = restante
                else:
                    parte = min(restante, round(valor * perda / soma, 1))
                ajustados.append(round(max(0.0, parte), 1))
                restante = round(restante - parte, 1)
            valores = ajustados
            for item in itens:
                item["ajuste_desconto"] = "Valor ajustado proporcionalmente para corresponder à perda do critério."

        for item, valor in zip(itens, valores):
            if valor > 0:
                item["desconto"] = round(valor, 1)
                resultado.append(item)

        falta = round(perda - sum(valor for item, valor in zip(itens, valores) if valor > 0), 1)
        if falta > 0:
            resultado.append({
                "criterio": nome,
                "problema": "Parcela restante da perda não discriminada por erro específico",
                "desconto": falta,
                "justificativa": "A parcela completa a diferença entre a nota do critério e a nota máxima, sem atribuí-la a um erro que a IA não apontou.",
            })

    return resultado
