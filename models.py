import csv
from collections import Counter
from datetime import datetime, timedelta
import locale
import os

# --------------------------------------------------------------------------------
#   LEITURA DO CSV EM MEMÓRIA
# --------------------------------------------------------------------------------

def importar_csv_mem(caminho_csv="placas.csv"):
    """Lê o CSV rapidamente e retorna lista de registros ordenados do mais novo para o mais antigo."""
    registros = []

    if not os.path.exists(caminho_csv):
        return registros

    with open(caminho_csv, newline='', encoding='utf-8', buffering=131072) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not row.get("Nº placa"):
                continue

            data_str = (row.get("Hora") or "").strip()
            data_ts = _parse_to_timestamp(data_str)

            registros.append({
                "indice": row.get("Índice"),
                "pista": row.get("Pista"),
                "tam_kb": row.get("Tam. (KB)"),
                "datahora": data_str,
                "timestamp": data_ts,
                "nplaca": row.get("Nº placa"),
                "marca": row.get("Marca"),
                "cor_placa": row.get("Cor placa"),
                "cor_veiculo": row.get("Cor veículo"),
                "veloc_kmh": row.get("Veloc.km/h"),
                "regiao": row.get("Região"),
                "tipo_evento": row.get("Tipo evento"),
                "tamanho_veiculo": row.get("Tam. Veíc."),
            })

    # Filtra inválidos
    registros = [r for r in registros if r.get("timestamp", 0) > 0]

    # Ordena por data (decrescente)
    registros.sort(key=lambda r: r["timestamp"], reverse=True)

    print(f"📄 CSV carregado: {len(registros)} registros | Mais recente: {registros[0]['datahora'] if registros else 'N/A'}")

    return registros


# --------------------------------------------------------------------------------
#   PARSE DE DATA ROBUSTO
# --------------------------------------------------------------------------------

def _parse_to_timestamp(data_str: str) -> float:
    if not data_str:
        return 0.0

    formatos = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]
    for fmt in formatos:
        try:
            return datetime.strptime(data_str, fmt).timestamp()
        except:
            pass

    try:
        return datetime.fromisoformat(data_str.replace("Z", "")).timestamp()
    except:
        return 0.0


# --------------------------------------------------------------------------------
#   FILTRAR SEM PERDER ORDEM
# --------------------------------------------------------------------------------

def filtrar_registros_mem(registros, placa=None, regiao=None, data=None):
    placa = (placa or "").strip().lower()
    regiao = (regiao or "").strip().lower()
    data = (data or "").strip()

    result = []
    for r in registros:
        if placa and placa not in (r.get("nplaca") or "").lower():
            continue
        if regiao and regiao != "todos" and regiao != (r.get("regiao") or "").lower():
            continue
        if data and not (r.get("datahora") or "").startswith(data):
            continue
        result.append(r)

    return sorted(result, key=lambda r: r["timestamp"], reverse=True)


# --------------------------------------------------------------------------------
#   RESUMO GERAL
# --------------------------------------------------------------------------------

def resumo_mem(registros):
    total = len(registros)
    regioes = len({(r.get("regiao") or "") for r in registros if r.get("regiao")})

    vel = []
    for r in registros:
        try:
            vel.append(float(str(r.get("veloc_kmh") or "0").replace(",", ".")))
        except:
            pass
    media = round(sum(vel)/len(vel), 1) if vel else 0.0

    crit = len([1 for r in registros if _to_float(r.get("veloc_kmh")) > 80])

    return {
        "total": total,
        "regioes": regioes,
        "veloc_media": media,
        "eventos_criticos": crit
    }


def _to_float(x):
    try:
        return float(str(x).replace(",", "."))
    except:
        return 0.0


# --------------------------------------------------------------------------------
#   ESTATÍSTICAS COMPLETAS (CORRIGIDO!)
# --------------------------------------------------------------------------------

def estatisticas(registros):
    """Gera estatísticas completas para o dashboard e painel analítico."""
    from statistics import mean

    por_hora = Counter()
    por_dia_semana = Counter()
    por_mes = Counter()
    por_regiao = Counter()
    placas = Counter()
    velocidade_dia = {}
    velocidade_faixa = Counter()
    por_horadia = Counter()

    hoje = datetime.now()

    dia_semana = hoje.weekday()  # 0 = segunda
    segunda = hoje - timedelta(days=dia_semana)
    domingo = segunda + timedelta(days=6)

    por_semana_atual = Counter()
    por_ultimos7 = Counter()

    nomes_semana = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    for r in registros:
        ts = r.get("timestamp", 0)
        if not ts:
            continue

        data = datetime.fromtimestamp(ts)
        data_label = data.strftime("%d/%m")
        mes_label = data.strftime("%b/%Y").capitalize()
        hora_label = data.strftime("%Hh")

        # -----------------------------------------
        # HORAS (já existia)
        # -----------------------------------------
        por_hora[hora_label] += 1

        # -----------------------------------------
        # DIA DA SEMANA (NOVO!)
        # -----------------------------------------
        indice = data.weekday()  # 0=Seg → 6=Dom
        nome_dia = nomes_semana[indice]
        por_dia_semana[nome_dia] += 1

        # -----------------------------------------
        # SEMANAL
        # -----------------------------------------
        if segunda.date() <= data.date() <= domingo.date():
            por_semana_atual[data_label] += 1

        if data >= hoje - timedelta(days=7):
            por_ultimos7[data_label] += 1

        # -----------------------------------------
        # MENSAL
        # -----------------------------------------
        por_mes[mes_label] += 1

        # -----------------------------------------
        # REGIÃO
        # -----------------------------------------
        por_regiao[r.get("regiao", "N/A")] += 1

        # -----------------------------------------
        # PLACAS
        # -----------------------------------------
        placas[r.get("nplaca", "N/A")] += 1

        # -----------------------------------------
        # VELOCIDADE
        # -----------------------------------------
        try:
            v = float(str(r.get("veloc_kmh") or "0").replace(",", "."))
        except:
            v = 0.0

        velocidade_dia.setdefault(data_label, []).append(v)

        if v <= 30: velocidade_faixa["0-30"] += 1
        elif v <= 60: velocidade_faixa["31-60"] += 1
        elif v <= 90: velocidade_faixa["61-90"] += 1
        elif v <= 120: velocidade_faixa["91-120"] += 1
        else: velocidade_faixa["121+"] += 1

        por_horadia[(data.weekday(), data.hour)] += 1

    # ----------------------------
    # SEMANAL LÓGICA INTELIGENTE
    # ----------------------------
    por_semana = por_semana_atual or por_ultimos7

    def sort_ddmm(x):
        return datetime.strptime(x, "%d/%m")

    por_semana = dict(sorted(por_semana.items(), key=lambda x: sort_ddmm(x[0])))
    por_mes = dict(sorted(por_mes.items()))
    por_regiao = dict(sorted(por_regiao.items()))
    por_hora = dict(sorted(por_hora.items()))

    # velocidade média por dia
    velocidade_semana = {
        k: round(sum(vs) / len(vs), 1) for k, vs in velocidade_dia.items()
    }
    velocidade_semana = dict(sorted(velocidade_semana.items(), key=lambda x: sort_ddmm(x[0])))

    topo_placas = dict(placas.most_common(10))
    pico_horas = {f"{d}-{h}": v for (d, h), v in por_horadia.items()}

    # ----------------------------
    # RETORNO FINAL
    # ----------------------------
    return {
        "diario": por_dia_semana,          # <-- AGORA SIM!
        "semanal": por_semana,
        "mensal": por_mes,
        "regiao": por_regiao,
        "velocidade_semana": velocidade_semana,
        "velocidade_faixa": velocidade_faixa,
        "top_placas": topo_placas,
        "pico_horas": pico_horas,
    }
