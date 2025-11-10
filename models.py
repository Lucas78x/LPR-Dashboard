import csv
from collections import Counter
from datetime import datetime, timedelta
import locale
import os

# -------- CSV EM MEMÓRIA --------
def importar_csv_mem(caminho_csv="placas.csv"):
    """Lê o CSV rapidamente e retorna uma lista de dicionários ordenada do mais novo para o mais antigo."""
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

    # Remove registros sem timestamp válido
    registros = [r for r in registros if r.get("timestamp", 0) > 0]

    # Ordena do mais novo pro mais antigo
    registros.sort(key=lambda r: r["timestamp"], reverse=True)

    print(f"✅ CSV carregado: {len(registros)} registros, mais recente: {registros[0]['datahora'] if registros else 'N/A'}")

    return registros


def _parse_to_timestamp(data_str: str) -> float:
    """Converte string de data em timestamp (robusto para múltiplos formatos)."""
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
        except Exception:
            continue

    # fallback: tenta ISO parcial (ex: 2025-11-08T09:00)
    try:
        return datetime.fromisoformat(data_str.replace("Z", "")).timestamp()
    except Exception:
        return 0.0


def filtrar_registros_mem(registros, placa=None, regiao=None, data=None):
    """Filtra e mantém ordem decrescente (mais novos primeiro)."""
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

    # registros já estão em ordem decrescente no carregamento
    return result


def resumo_mem(registros):
    total = len(registros)
    regioes = len({(r.get("regiao") or "") for r in registros if r.get("regiao")})

    vel = []
    for r in registros:
        try:
            v = float(str(r.get("veloc_kmh") or "0").replace(",", "."))
            vel.append(v)
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

def estatisticas(registros):
    """Gera estatísticas completas para o dashboard e painel analítico, incluindo picos de horário (heatmap)."""
    from statistics import mean

    por_hora = Counter()
    por_horadia = Counter()  # (dia_semana, hora)
    por_semana = Counter()
    por_mes = Counter()
    por_regiao = Counter()
    velocidade_dia = {}       # para média de velocidade por data
    velocidade_faixa = Counter()
    placas = Counter()

    for r in registros:
        ts = r.get("timestamp", 0)
        if not ts:
            continue
        data = datetime.fromtimestamp(ts)
        data_label = data.strftime("%d/%m")   # para semanal
        mes_label = data.strftime("%b/%Y").capitalize()
        hora_label = data.strftime("%Hh")

        # contadores básicos
        por_hora[hora_label] += 1
        por_semana[data_label] += 1
        por_mes[mes_label] += 1
        por_regiao[r.get("regiao", "N/A")] += 1
        placas[r.get("nplaca", "N/A")] += 1

        # velocidade média diária
        try:
            v = float(str(r.get("veloc_kmh") or "0").replace(",", "."))
        except:
            v = 0.0
        velocidade_dia.setdefault(data_label, []).append(v)

        # faixas de velocidade
        if v <= 30:
            velocidade_faixa["0-30"] += 1
        elif v <= 60:
            velocidade_faixa["31-60"] += 1
        elif v <= 90:
            velocidade_faixa["61-90"] += 1
        elif v <= 120:
            velocidade_faixa["91-120"] += 1
        else:
            velocidade_faixa["121+"] += 1

        # picos por dia da semana × hora
        dia_semana = data.weekday()  # 0=Seg, 6=Dom
        hora = data.hour
        por_horadia[(dia_semana, hora)] += 1

    # calcula médias de velocidade por data
    velocidade_semana = {
        k: round(mean(vs), 1) for k, vs in velocidade_dia.items()
    }

    # limita top 10 placas
    top_placas = dict(placas.most_common(10))

    # prepara dados do heatmap
    # formata como {"0-14": 5, "3-8": 12, ...}
    pico_horas = {f"{d}-{h}": v for (d, h), v in por_horadia.items()}

    # ordenação
    por_hora = dict(sorted(por_hora.items()))
    por_semana = dict(sorted(
        por_semana.items(), key=lambda x: datetime.strptime(x[0], "%d/%m")))
    velocidade_semana = dict(sorted(
        velocidade_semana.items(), key=lambda x: datetime.strptime(x[0], "%d/%m")))
    por_mes = dict(sorted(por_mes.items()))
    por_regiao = dict(sorted(por_regiao.items()))
    velocidade_faixa = dict(velocidade_faixa)
    top_placas = dict(sorted(top_placas.items(), key=lambda x: x[1], reverse=True))

    return {
        "diario": por_hora,
        "semanal": por_semana,
        "mensal": por_mes,
        "regiao": por_regiao,
        "velocidade_semana": velocidade_semana,
        "velocidade_faixa": velocidade_faixa,
        "top_placas": top_placas,
        "pico_horas": pico_horas,   # <-- adicionado
    }

   
