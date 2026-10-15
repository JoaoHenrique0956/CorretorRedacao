from flask import Flask, request, jsonify, render_template, redirect ,session, flash
from openai import OpenAI
import json
import os

from pdf_historico import gerar_pdf_historico

from db.database import MysqlDatabase
import logging
import traceback

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "academic-write-ai-dev-secret")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)

#na linha abaixo é necessário inserir a API KEY da OPENAI
API_KEY = os.environ.get("OPENAI_API_KEY", "Coloque sua chave")

client = OpenAI(
    api_key=API_KEY
)
#informações do banco de dados
db = MysqlDatabase(
    host="127.0.0.1",
    user="root",
    password="",
    database="mydb"
)

logger.info("API_KEY carregada.")


@app.route("/")
def home():
    return render_template("Index.html")

#como definimos as notas
def nivel_qualitativo(nota):
    nota = float(nota or 0)
    if nota >= 9: return "Excelente"
    if nota >= 7: return "Bom"
    if nota >= 5: return "Regular"
    return "Insuficiente"

@app.route("/salvar_texto", methods=["POST"])
def salvar_texto():

    if "idUsuario" not in session:
        return redirect("/login")

    titulo = request.form.get("titulo")
    conteudo = request.form.get("conteudo")
    tema = request.form.get("tema")
    genero = request.form.get("genero")

    conn = db.get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Texto (titulo, conteudo, Usuario_idUsuario, genero, tema)
        VALUES (%s, %s, %s, %s, %s)
    """, (titulo, conteudo, session["idUsuario"], genero, tema))

    conn.commit()

    cursor.execute("SELECT LAST_INSERT_ID()")
    id_texto = cursor.fetchone()[0]

    session["idTexto"] = id_texto

    cursor.close()
    conn.close()

    return redirect("/historico")

@app.route("/historico")
def historico():

    if "idUsuario" not in session:
        return redirect("/login")

    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
    SELECT
        t.idTexto,
        t.titulo,
        t.conteudo,
        c.nota,
        c.nEstrutura,
        c.nTema,
        c.nGramatica,
        c.nRepertorio,
        c.nCoesao,
        c.recomendacoes,
        c.data_correcao,
        t.genero,
        t.tema
    FROM Texto t
    INNER JOIN correcoes c
        ON c.Texto_idTexto = t.idTexto
    WHERE t.Usuario_idUsuario = %s
    ORDER BY c.data_correcao DESC
    """,
    (session["idUsuario"],))

    historico = cursor.fetchall()

    for item in historico:
        try:
            item["feedback"] = json.loads(item.get("recomendacoes") or "{}")
        except json.JSONDecodeError:
            item["feedback"] = {}
        item["feedback"]["detalhes_descontos"] = [
            desconto for desconto in item["feedback"].get("detalhes_descontos", [])
            if isinstance(desconto, dict)
            and desconto.get("problema") not in ("Parcela restante da perda não discriminada por erro específico", "Perda do critério não detalhada em erros individuais")
        ] if isinstance(item["feedback"].get("detalhes_descontos"), list) else []

        item["data_formatada"] = (
            item["data_correcao"].strftime("%d/%m/%Y %H:%M")
            if item.get("data_correcao")
            else "Sem data"
        )
        item["nivel"] = nivel_qualitativo(item.get("nota"))

    historico_json = [
        {
            "id": item.get("idTexto"),
            "titulo": item.get("titulo") or "Redação sem título",
            "conteudo": item.get("conteudo") or "Texto não encontrado.",
            "nota": float(item.get("nota") or 0),
            "nEstrutura": float(item.get("nEstrutura") or 0),
            "nTema": float(item.get("nTema") or 0),
            "nGramatica": float(item.get("nGramatica") or 0),
            "nRepertorio": float(item.get("nRepertorio") or 0),
            "nCoesao": float(item.get("nCoesao") or 0),
            "data": item.get("data_formatada"),
            "nivel": item.get("nivel"),
            "genero": item.get("genero") or "Não informado",
            "tema": item.get("tema") or "Tema livre",
            "feedback": item.get("feedback") or {}
        }
        for item in historico
    ]

    cursor.close()
    conn.close()

    return render_template(
        "Historico.html",
        historico=historico,
        historico_json=historico_json
    )


@app.route("/historico/<int:id_texto>/excluir", methods=["POST"])
def excluir_redacao(id_texto):
    if "idUsuario" not in session:
        return redirect("/login")
    conn = cursor = None
    try:
        conn = db.get_connection()
        conn.start_transaction()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT idTexto FROM Texto WHERE idTexto=%s AND Usuario_idUsuario=%s",
            (id_texto, session["idUsuario"])
        )
        if not cursor.fetchone():
            conn.rollback()
            flash("Redação não encontrada no seu histórico.", "warning")
            return redirect("/historico")
        cursor.execute("DELETE FROM correcoes WHERE Texto_idTexto=%s", (id_texto,))
        cursor.execute(
            "DELETE FROM Texto WHERE idTexto=%s AND Usuario_idUsuario=%s",
            (id_texto, session["idUsuario"])
        )
        conn.commit()
        flash("Redação excluída do histórico.", "success")
    except Exception:
        if conn:
            conn.rollback()
        logger.exception("Falha ao excluir redação do histórico")
        flash("Não foi possível excluir a redação agora. Tente novamente.", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return redirect("/historico")

@app.route("/historico/<int:id_texto>/pdf")
def exportar_historico_pdf(id_texto):
    if "idUsuario" not in session:
        return redirect("/login")
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.idTexto, t.titulo, t.conteudo, t.genero, t.tema,
               c.nota, c.nEstrutura, c.nTema, c.nGramatica,
               c.nRepertorio, c.nCoesao, c.recomendacoes, c.data_correcao
        FROM Texto t
        INNER JOIN correcoes c ON c.Texto_idTexto = t.idTexto
        WHERE t.idTexto=%s AND t.Usuario_idUsuario=%s
        ORDER BY c.data_correcao DESC
        LIMIT 1
    """, (id_texto, session["idUsuario"]))
    item = cursor.fetchone()
    cursor.close()
    conn.close()
    if not item:
        flash("Redação não encontrada no seu histórico.", "warning")
        return redirect("/historico")
    try:
        item["feedback"] = json.loads(item.get("recomendacoes") or "{}")
    except (TypeError, json.JSONDecodeError):
        item["feedback"] = {}
    item["feedback"]["detalhes_descontos"] = [
        desconto for desconto in item["feedback"].get("detalhes_descontos", [])
        if isinstance(desconto, dict)
        and desconto.get("problema") not in ("Parcela restante da perda não discriminada por erro específico", "Perda do critério não detalhada em erros individuais")
    ] if isinstance(item["feedback"].get("detalhes_descontos"), list) else []
    item["nivel"] = nivel_qualitativo(item.get("nota"))
    item["data_formatada"] = item["data_correcao"].strftime("%d/%m/%Y %H:%M") if item.get("data_correcao") else "Sem data"
    return gerar_pdf_historico(item)
    
    

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")
        conn = cursor = None
        try:
            conn = db.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Usuario WHERE email=%s AND senha=%s", (email, senha))
            usuario = cursor.fetchone()
        except Exception:
            logger.exception("Falha durante autenticação")
            return render_template("Login.html", erro="Não foi possível entrar agora. Tente novamente."), 503
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        if not usuario:
            return render_template_string("Login.html", erro="Email ou senha inválidos.", email=email)

        session["idUsuario"] = usuario["idUsuario"]
        session["nome"] = usuario["nome"]

        return redirect("/")

    return render_template("Login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/sobre")
def sobre():
    return render_template("Sobre.html")

@app.route("/redacoes-modelo")
def redacoes_modelo():
    conn = db.get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM redacoes_modelo ORDER BY titulo")
    modelos = cursor.fetchall()
    for modelo in modelos:
        try:
            modelo["feedback"] = json.loads(modelo.get("recomendacoes") or "{}")
        except (TypeError, json.JSONDecodeError):
            modelo["feedback"] = {}
        modelo["nivel"] = nivel_qualitativo(modelo.get("nota"))
    cursor.close()
    conn.close()
    return render_template("Modelos.html", modelos=modelos)

@app.route("/cadastro", methods=["POST"])
def cadastro():

    nome = request.form["nome"]
    email = request.form["email"]
    senha = request.form["senha"]

    try:

        conn = db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO Usuario(nome,email,senha)
            VALUES (%s,%s,%s)
            """,
            (nome,email,senha)
        )

        conn.commit()

        cursor.close()
        conn.close()
        

        return redirect("/login")

    except Exception as e:

        return f"Erro: {str(e)}"

logger.info("Enviando requisição para a API OpenAi...")

@app.route("/corrigir", methods=["POST"])

def corrigir():

    if not API_KEY:
        return jsonify({
            "erro": "API KEY não definida."
        })

    data = request.get_json(silent=True) or {}

    texto = data.get("texto", "").strip()
    genero = data.get("genero", "").strip()
    assunto = data.get("tema", "").strip()
    imagem = data.get("imagem")
    if imagem:
        import re
        match = re.fullmatch(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)", imagem)
        if not match:
            return jsonify({"erro": "Imagem inválida. Envie PNG, JPG ou WebP."}), 400
        if len(match.group(2)) > 7_000_000:
            return jsonify({"erro": "A imagem excede o limite de 5 MB."}), 413
        imagem_url = imagem

    logger.debug(f"Texto recebido: {texto[:150]}")
    logger.debug(f"Gênero recebido: {genero}")
    logger.debug(f"tema recebido: {assunto}")

    if not texto and not imagem:
        return jsonify({
            "erro": "Digite a redação ou selecione uma imagem."
        }), 400




#NO PROMPT ABAIXO DEFINIMOS COMO A REDAÇÃO SERÁ CORRIGIDA



    prompt = f"""
Atue como um corretor de redação rigido, mas nem tanto , crítico , imparcial e principalmente justo , a fim de expor as melhorias sobre o gênero textual: {genero}


Normas exigidas para a correção:

*Estrutura do Texto:*
O texto deve seguir rigidamente as normas do gênero escolhido, não abrindo espaço para exceções.

*Tema:*
Caso seja Fornecido um tema específico ao texto, verifique se ele permanece no mesmo tema do início ao fim do texto em casos de desvio total todos os atributos serão atribuidos a nota ZERO.

*Gramática:*
Busque por erros gramaticais, ou erros de coerência e destaque-os ,busque seguir a norma culta da língua portuguesa, em casos de gêneros textuais que não admitem Oralidade, pontue os trechos que a possuem e descorte nota de acordo.

*(situacional) Análise de Repertório:*
caso o gênero textual tenha a necessidade de possuir argumentos e repertório, analise a existência desses argumentos/repertórios e julgue a pertinência deles em relação ao tema , valorize repertório como obras audiovisuais , voz de autoridade e conhecimento da autalidade global , CASO O GENERO TEXTUAL NÃO TENHA COMO POSSUIR REPERTÓRIO ATRIBUA 10.

*Coesão Textual:*
Busque por erros de Coesão Textual no texto, analise a presença da articuladores textuais, se eles fazem sentido com o período e se o texto flui bem.

*nota:*
Após a análise dos critérios anteriores, faça uma estimativa de nota para cada um dos critérios e logo depois uma estimativa geral (dê preferencia a uma média aritimética das notas dos critérios), variando de 0-10.

A nota deve conter até no máximo 1 casa decimal, não arredonde a nota.

Recomendações:
Aponte o que e como deve ser melhorado, destacando o critério e o que deve mudar.

→ Não Reescreva a redação ←

O tema será:
{assunto}

O texto analisado será:
{texto}

Responda APENAS em JSON válido no seguinte formato:

{{
"txtStruct": "",
"txtTema": "",
"txtGeC": "",
"txtRep": "",
"txtCoe": "",
"txtNota": "",
"txtTip": "",

"nota_estrutura": 0,
"nota_tema": 0,
"nota_gramatica": 0,
"nota_repertorio": 0,
"nota_coesaoTextual": 0,
"texto_transcrito": "",
"highlights": [{{"trecho": "trecho exato da redação", "criterio": "Gramática", "comentario": "explicação"}}],
"detalhes_descontos": [{{"criterio": "Gramática", "problema": "descrição", "desconto": null, "justificativa": "explicação"}}]
    
}}

Regras:
- Não escreva nada fora do JSON
- Não use markdown
- Não use ```json
- Todas as respostas devem ser breves, claras e diretas
- As respostas devem conter APENAS o que precisa ser corrigido
- Não faça elogios
- Em detalhes_descontos, inclua exatamente um item para cada critério: Estrutura, Tema, Gramática, Repertório e Coesão Textual.
- O desconto de cada critério deve ser igual a 10 menos a nota atribuída a esse critério; informe 0 quando a nota for 10.
- Se o desconto for maior que 0, explique-o com base na avaliação do critério e nos problemas já apontados, sem inventar erros. Se for 0, use problema "Sem desconto" e justificativa "Critério recebeu nota máxima.".
"""

    try:

        user_content = prompt
        if imagem:
            user_content = [
                {"type": "text", "text": prompt + "\nLeia o texto da imagem e corrija-o. Inclua a transcrição completa em texto_transcrito. Se estiver ilegível, informe isso em txtTip."},
                {"type": "image_url", "image_url": {"url": imagem_url, "detail": "high"}}
            ]
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um corretor de redações e deve responder apenas JSON válido."
                },
                {
                    "role": "user",
                    "content": user_content
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )

        resultado = response.choices[0].message.content

    except Exception as e:

        logger.error(str(e))

        return jsonify({
            "erro": "Não foi possível processar a correção agora. Tente novamente."
        }), 502

    resultado = (
        resultado
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:

        resultado_dict = json.loads(resultado)

        print(json.dumps(resultado_dict, indent=4, ensure_ascii=False))

        estrutura = resultado_dict.get("txtStruct", "")
        tema = resultado_dict.get("txtTema", "")
        gec = resultado_dict.get("txtGeC", "")
        repertorio = resultado_dict.get("txtRep", "")
        coesaoTextual = resultado_dict.get("txtCoe", "")
        nota = resultado_dict.get("txtNota", "")
        dicas = resultado_dict.get("txtTip", "")

        def para_float(valor):
            try:
                return round(max(0.0, min(10.0, float(valor))), 1)
            except (TypeError, ValueError):
                return 0

        nota_estrutura = para_float(
            resultado_dict.get("nota_estrutura", 0)
        )
        nota_tema = para_float(
            resultado_dict.get("nota_tema", 0)
        )
        nota_gramatica = para_float(
            resultado_dict.get("nota_gramatica", 0)
        )
        nota_repertorio = para_float(
            resultado_dict.get("nota_repertorio", 0)
        )
        nota_coesaoTextual = para_float(
            resultado_dict.get("nota_coesaoTextual", 0)
        )

        # Define se o gênero exige avaliação de repertório.
        genero_exige_repertorio = genero in (
            "Dissertação Argumentativa",
            "Artigo de Opinião"
        )

        if not genero_exige_repertorio:
            nota_repertorio = 10
            repertorio = (
                "Critério não aplicável a este gênero textual."
            )

        if isinstance(nota, dict):
            nota = f"Nota geral: {nota.get('Geral', '--')}"

        # A nota geral é exclusivamente a média aritmética dos cinco critérios.
        # Os descontos já estão refletidos nas notas individuais.
        notas_aplicaveis = [
            nota_estrutura,
            nota_tema,
            nota_gramatica,
            nota_coesaoTextual
        ]

        if genero_exige_repertorio:
            notas_aplicaveis.append(nota_repertorio)

        media = sum(notas_aplicaveis) / len(notas_aplicaveis)

        descontos = resultado_dict.get("detalhes_descontos", [])
        if not isinstance(descontos, list):
            descontos = []

        if not genero_exige_repertorio:
            descontos = [
                item for item in descontos
                if item.get("criterio") != "Repertório"
            ]

            descontos.append({
                "criterio": "Repertório",
                "problema": "Critério não aplicável",
                "desconto": 0,
                "justificativa": (
                    "Este gênero textual não exige avaliação de repertório."
                )
            })
        
        texto = (resultado_dict.get("texto_transcrito") or texto).strip()
        if imagem and not texto:
            return jsonify({"erro": "Não foi possível ler a redação na imagem. Envie uma foto mais nítida ou digite o texto."}), 422

        if "idUsuario" in session:
            conn = db.get_connection()
            cursor = conn.cursor()

            titulo = texto.strip().splitlines()[0][:80] if texto.strip() else "Redação sem título"

            cursor.execute("""
                INSERT INTO Texto (titulo, conteudo, Usuario_idUsuario, genero, tema)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                titulo,
                texto,
                session["idUsuario"], genero, assunto
            ))

            id_texto = cursor.lastrowid
            session["idTexto"] = id_texto

            cursor.execute("""
                INSERT INTO correcoes
                (nota, nEstrutura, nTema, nGramatica, nRepertorio, nCoesao, recomendacoes, data_correcao, Texto_idTexto)
                VALUES (%s,%s,%s,%s,%s,%s,%s,NOW(),%s)
            """, (
                media,
                nota_estrutura,
                nota_tema,
                nota_gramatica,
                nota_repertorio,
                nota_coesaoTextual,
                json.dumps({
                    "txtStruct": estrutura,
                    "txtTema": tema,
                    "txtGeC": gec,
                    "txtRep": repertorio,
                    "txtCoe": coesaoTextual,
                    "txtTip": dicas
                    ,"highlights": resultado_dict.get("highlights", [])
                    ,"detalhes_descontos": descontos
                }, ensure_ascii=False),
                id_texto
            ))

            conn.commit()
            cursor.close()
            conn.close()
        
     
        

        return jsonify({
"txtStruct": estrutura,
"txtTema": tema,
"txtGeC": gec,
"txtRep": repertorio,
"txtCoe": coesaoTextual,
"txtNota": f"{media:.1f}",
"txtTip": dicas,

"nota_estrutura": nota_estrutura,
"nota_tema": nota_tema,
"nota_gramatica": nota_gramatica,
"nota_repertorio": nota_repertorio,
"nota_coesaoTextual": nota_coesaoTextual
,"texto_transcrito": texto
,"highlights": resultado_dict.get("highlights", [])
,"detalhes_descontos": descontos

})
        
        

    except json.JSONDecodeError as e:

        logger.error("Erro ao converter JSON da IA")
        logger.error(str(e))
        logger.error(f"Resposta recebida: {resultado}")

        return jsonify({
            "erro": "Não foi possível interpretar o resultado da correção. Tente novamente."
        })

    except Exception as e:

        logger.error("ERRO GERAL")
        logger.error(str(e))
        logger.error(traceback.format_exc())

        return jsonify({
            "erro": "Ocorreu um erro ao salvar ou preparar a correção. Tente novamente."
        }), 500
    


if __name__ == "__main__":
    app.run(debug=False)
