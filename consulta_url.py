import sys
import asyncio

if sys.platform.startswith("win"):
    # Força o uso do Proactor, que suporta criação de subprocessos no Windows.
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import nest_asyncio
nest_asyncio.apply()

import streamlit as st
import time
from urllib.parse import urlparse, urlunparse
from playwright.sync_api import sync_playwright
import pandas as pd

# Definindo constantes para os literais repetidos
RAW_URL_LABEL = "Raw URL"

# =======================
# Funções de Utilidade
# =======================
def normalize_url(url: str) -> str:
    """
    Normaliza a URL:
      - Se não iniciar com "http://" ou "https://", adiciona "https://".
      - Se a URL já estiver completa (com path, query ou fragment), não altera.
      - Só adiciona uma barra no final se *nem* path, query ou fragment estiverem presentes.
    """
    url = url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url
    parsed = urlparse(url)
    # Se não houver path, query nem fragment, define path como "/"
    if parsed.path == "" and not parsed.query and not parsed.fragment:
        parsed = parsed._replace(path="/")
    return urlunparse(parsed)

def check_urls(rows: list[dict]) -> list[dict]:
    """
    Para cada linha (dicionário com 'Nome' e 'URL'), normaliza a URL e tenta acessá-la
    usando o Playwright. Se o campo 'Nome' estiver vazio, registra erro.
    Retorna uma lista de dicionários com os resultados.
    """
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            }
        )
        page = context.new_page()
        for row in rows:
            name = str(row.get("Nome", "")).strip()
            raw_url = str(row.get("URL", "")).strip()
            if not name:
                results.append({
                    "Nome": "<sem nome>",
                    RAW_URL_LABEL: raw_url,
                    "Normalized": "",
                    "Status": "Erro",
                    "Code": "",
                    "Message": "Campo Nome é obrigatório."
                })
                continue
            if not raw_url:
                results.append({
                    "Nome": name,
                    RAW_URL_LABEL: raw_url,
                    "Normalized": "",
                    "Status": "Erro",
                    "Code": "",
                    "Message": "Campo URL é obrigatório."
                })
                continue
            norm_url = normalize_url(raw_url)
            try:
                response = page.goto(norm_url, wait_until="domcontentloaded", timeout=10000)
                if response and response.status == 200:
                    results.append({
                        "Nome": name,
                        RAW_URL_LABEL: raw_url,
                        "Normalized": norm_url,
                        "Status": "Online",
                        "Code": response.status,
                        "Message": ""
                    })
                else:
                    status_code = response.status if response else "Nenhum"
                    results.append({
                        "Nome": name,
                        RAW_URL_LABEL: raw_url,
                        "Normalized": norm_url,
                        "Status": "Erro",
                        "Code": status_code,
                        "Message": ""
                    })
            except Exception as e:
                results.append({
                    "Nome": name,
                    RAW_URL_LABEL: raw_url,
                    "Normalized": norm_url,
                    "Status": "Erro",
                    "Code": "Exception",
                    "Message": str(e)
                })
        browser.close()
    return results

# =======================
# Configuração Inicial
# =======================
# Lista padrão de URLs com Nome e URL
default_data = [
    {"Nome": "TJAC", "URL": "https://esaj.tjac.jus.br/cpopg/open.do"},
    {"Nome": "TJAL", "URL": "https://www2.tjal.jus.br/cpopg/open.do"},
    {"Nome": "TJam", "URL": "https://consultasaj.tjam.jus.br/cpopg/open.do"},
    {"Nome": "Projudi TJam", "URL": "https://projudi.tjam.jus.br/projudi/processo/consultaPublicaNova.do?actionType=iniciar"},
    {"Nome": "TJAP", "URL": "https://pje.tjap.jus.br/1g/ConsultaPublica/listView.seam"},
    {"Nome": "TJBA (esaj)", "URL": "http://esaj.tjba.jus.br/cpopg/open.do"},
    {"Nome": "Projudi TJBA", "URL": "https://projudi.tjba.jus.br/projudi/"},
    {"Nome": "TJBA (consulta pública)", "URL": "https://consultapublicapje.tjba.jus.br/pje/ConsultaPublica/listView.seam"},
    {"Nome": "TJCE", "URL": "https://esaj.tjce.jus.br/cpopg/open.do"},
    {"Nome": "TJDFT", "URL": "https://pje-consultapublica.tjdft.jus.br/consultapublica/ConsultaPublica/listView.seam"},
    {"Nome": "TJES", "URL": "https://pje.tjes.jus.br/pje/ConsultaPublica/listView.seam"},
    {"Nome": "TJGO", "URL": "https://pjd.tjgo.jus.br/BuscaProcessoPublica?PaginaAtual=2&Passo=7"},
    {"Nome": "TJMA", "URL": "https://pje.tjma.jus.br/pje/ConsultaPublica/listView.seam"},
    {"Nome": "TJMT", "URL": "https://pje.tjmt.jus.br/pje/ConsultaPublica/listView.seam"},
    {"Nome": "TJMS", "URL": "https://esaj.tjms.jus.br/cpopg5/open.do"},
    {"Nome": "TJMG (consulta pública)", "URL": "https://pje-consulta-publica.tjmg.jus.br/"},
    {"Nome": "TJMG (andamento)", "URL": "https://www.tjmg.jus.br/portal-tjmg/processos/andamento-processual/"},
    {"Nome": "TJPA", "URL": "https://projudi.tjpa.jus.br/projudi/"},
    {"Nome": "TJPB", "URL": "https://pje.tjpb.jus.br/pje-corregedoria/ConsultaPublica/listView.seam"},
    {"Nome": "TJPR", "URL": "https://consulta.tjpr.jus.br/projudi_consulta/"},
    {"Nome": "TJPE", "URL": "https://srv01.tjpe.jus.br/consultaprocessualunificada/processo/"},
    {"Nome": "TJPI", "URL": "https://pje.tjpi.jus.br/1g/ConsultaPublica/listView.seam"},
    {"Nome": "TJRJ (por número)", "URL": "https://www3.tjrj.jus.br/consultaprocessual/#/consultapublica#porNumero"},
    {"Nome": "TJRJ (por nome)", "URL": "https://www3.tjrj.jus.br/consultaprocessual/#/consultapublica#porNome"},
    {"Nome": "TJRJ", "URL": "https://tjrj.pje.jus.br/1g/ConsultaPublica/listView.seam"},
    {"Nome": "TJRN", "URL": "https://pje1g.tjrn.jus.br/pje/ConsultaPublica/listView.seam"},
    {"Nome": "TJRS (eproc busca)", "URL": "https://consulta-processual-service.tjrs.jus.br/api/consulta-service/v1/eprocBuscaPorNomesDaParte?totalRegistrosPorPagina=500&numeroPagina=1&nomeParte=FINCH%20SOLU%C3%87%C3%95ES&tipoPesquisa=F&situacao=A&perfil=0"},
    {"Nome": "TJRS (eproc principal)", "URL": "https://eproc1g.tjrs.jus.br/eproc/externo_controlador.php?acao=principal"},
    {"Nome": "TJRO", "URL": "https://pjepg-consulta.tjro.jus.br/consulta/ConsultaPublica/listView.seam"},
    {"Nome": "TJRR", "URL": "https://projudi.tjrr.jus.br/projudi/"},
    {"Nome": "TJSC", "URL": "https://eprocwebcon.tjsc.jus.br/consulta1g/externo_controlador.php?acao=processo_consulta_publica"},
    {"Nome": "TJSE", "URL": "https://www.tjse.jus.br/portal/consultas/consulta-processual"},
    {"Nome": "TJSP", "URL": "https://esaj.tjsp.jus.br/cpopg/open.do"},
    {"Nome": "TJTO", "URL": "https://eproc1.tjto.jus.br/eprocV2_prod_1grau/externo_controlador.php?acao=tjto@md_tjto_consulta_publica/paginaLogin"},
]

# Inicializa o DataFrame no session_state se ainda não existir.
if "urls_df" not in st.session_state:
    st.session_state["urls_df"] = pd.DataFrame(default_data)

if "results" not in st.session_state:
    st.session_state["results"] = []

# =======================
# Interface do Aplicativo
# =======================
st.title("Dashboard de Monitoramento de URLs")
st.write("Preencha/edite os campos abaixo e clique em **Verificar URLs** para monitorar os sites.")

# Editor de URLs usando st.data_editor (no topo da página)
edited_df = st.data_editor(
    st.session_state["urls_df"],
    num_rows="dynamic",
    key="editor",
    column_config={
        "Nome": st.column_config.TextColumn(
            "Nome", help="Campo obrigatório. Informe o nome identificador do site."
        ),
        "URL": st.column_config.TextColumn(
            "URL", help="Informe a URL completa (ex.: https://esaj.tjac.jus.br/cpopg/open.do)"
        )
    }
)

# Atualiza o DataFrame no session_state
st.session_state["urls_df"] = edited_df
data_rows = edited_df.to_dict("records")

if st.button("Verificar URLs"):
    with st.spinner("Verificando URLs..."):
        st.session_state["results"] = check_urls(data_rows)
    st.success("Verificação concluída!")

# =======================
# Exibição dos Resultados
# =======================
if st.session_state["results"]:
    st.subheader("Resultados:")
    for result in st.session_state["results"]:
        nome = result.get("Nome", "<sem nome>")
        raw_url = result.get(RAW_URL_LABEL, "")
        norm_url = result.get("Normalized", "")
        status = result.get("Status", "")
        code = result.get("Code", "")
        message = result.get("Message", "")
        # Se a URL normalizada for diferente da digitada, exibe ambos
        exibir_url = f"{raw_url} ➔ {norm_url}" if raw_url != norm_url else raw_url
        if status == "Online":
            st.markdown(
                f"""
                <div style='background-color: #d4edda; padding: 10px; border-radius: 5px; margin-bottom: 5px'>
                    <strong>{nome}</strong> - <em>{exibir_url}</em> - <span style='color: green;'>Online (status {code})</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style='background-color: #f8d7da; padding: 10px; border-radius: 5px; margin-bottom: 5px'>
                    <strong>{nome}</strong> - <em>{exibir_url}</em> - <span style='color: red;'>Erro (status {code})</span>
                    {"<br>Mensagem: " + message if message else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )