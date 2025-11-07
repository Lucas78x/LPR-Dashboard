import csv
from collections import Counter
import locale
from datetime import datetime, timedelta

# -------- CSV EM MEMÓRIA --------
def importar_csv_mem(caminho_csv="placas.csv"):
    """Lê o CSV e retorna uma lista de dicionários (sem gravar no DB)."""
    registros = []
    with open(caminho_csv, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if not row.get("Nº placa"):
                continue
            registros.append({
                "indice": row.get("Índice"),
                "pista": row.get("Pista"),
                "tam_kb": row.get("Tam. (KB)"),
                "datahora": row.get("Hora"),
                "nplaca": row.get("Nº placa"),
                "marca": row.get("Marca"),
                "cor_placa": row.get("Cor placa"),
                "cor_veiculo": row.get("Cor veículo"),
                "veloc_kmh": row.get("Veloc.km/h"),
                "regiao": row.get("Região"),
                "tipo_evento": row.get("Tipo evento"),
                "tamanho_veiculo": row.get("Tam. Veíc."),
            })
    return registros

def filtrar_registros_mem(registros, placa=None, regiao=None, data=None):
    result = []
    placa = (placa or "").strip().lower()
    regiao = (regiao or "").strip().lower()
    data = (data or "").strip()

    for r in registros:
        if placa and placa not in (r.get("nplaca") or "").lower():
            continue
        if regiao and regiao != "todos" and regiao != (r.get("regiao") or "").lower():
            continue
        if data and not (r.get("datahora") or "").startswith(data):
            continue
        result.append(r)

    # Ordena por data desc (quando possível)
    def _parse_dt(v):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(v, fmt)
            except:
                pass
        return None
    result.sort(key=lambda x: _parse_dt(x.get("datahora") or "") or datetime.min, reverse=True)
    return result

def resumo_mem(registros):
    # total filtrado
    total = len(registros)
    regioes = len({(r.get("regiao") or "") for r in registros if r.get("regiao")})
    # velocidade média (se numérica)
    vel = []
    for r in registros:
        try:
            v = float(str(r.get("veloc_kmh") or "0").replace(",", "."))
            vel.append(v)
        except:
            pass
    media = round(sum(vel)/len(vel), 1) if vel else 0.0

    # eventos críticos: exemplo velocidade > 80 km/h
    crit = len([1 for r in registros
                if r.get("veloc_kmh") and
                   _to_float(r.get("veloc_kmh")) > 80])

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
    def parse_data(valor):
        if not valor:
            return None
        formatos = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y/%m/%d %H:%M:%S"
        ]
        for fmt in formatos:
            try:
                return datetime.strptime(valor, fmt)
            except ValueError:
                continue
        return None

    por_hora = Counter()
    por_semana = Counter()
    por_mes = Counter()
    por_regiao = Counter()

    for r in registros:
        data = parse_data(r.get("datahora"))
        if not data:
            continue

        por_hora[data.strftime("%Hh")] += 1
        por_semana[data.strftime("%d/%m")] += 1
        por_mes[data.strftime("%b/%Y").capitalize()] += 1
        por_regiao[r.get("regiao", "N/A")] += 1

    por_hora = dict(sorted(por_hora.items()))
    por_semana = dict(sorted(por_semana.items(),
                             key=lambda x: datetime.strptime(x[0], "%d/%m")))
    por_mes = dict(sorted(por_mes.items()))
    por_regiao = dict(sorted(por_regiao.items()))

    return {
        "diario": por_hora,
        "semanal": por_semana,
        "mensal": por_mes,
        "regiao": por_regiao
    }
