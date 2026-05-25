from typing import List, Optional
import asyncio
import re
from datetime import date


SUSPICIOUS_TERMS = [
    "urgente", "preciso vender", "viagem", "doença", "financeiro",
    "troca por", "aceito proposta", "sem reserva", "relíquia", "colecionador",
    "único dono", "sem multa", "sem débito", "transferência imediata",
]

POSITIVE_TERMS = [
    "revisado", "revisão em dia", "manual", "chave reserva", "único dono",
    "sem batidas", "sem funilaria", "sem pintura", "ipva pago", "licenciado",
    "garantia de fábrica", "garantia",
]

KM_MEDIA_ANUAL = 15000


def _is_suspicious_price(
    preco: float,
    ano: Optional[int],
    preco_referencia: Optional[float] = None,
) -> bool:
    if preco <= 0:
        return False

    if preco_referencia and preco_referencia > 0 and preco / preco_referencia < 0.20:
        return True

    if ano:
        idade = max(0, date.today().year - ano)
        if idade <= 5 and preco < 10000:
            return True
        if idade <= 10 and preco < 5000:
            return True

    return preco < 3000


def _is_suspicious_km(km: int, ano: Optional[int]) -> bool:
    if km < 0 or not ano:
        return False

    idade = max(0, date.today().year - ano)
    if idade <= 1:
        return False

    km_esperado = max(1, idade * KM_MEDIA_ANUAL)
    ratio = km / km_esperado

    if km == 0:
        return True
    if idade >= 2 and km <= 500:
        return True
    if idade >= 4 and km <= 2000:
        return True
    if idade >= 8 and km <= 8000:
        return True
    if idade >= 12 and km <= 15000:
        return True

    return idade >= 3 and ratio < 0.08


def calcular_score(
    vehicle_data: dict,
    preco_medio_mercado: Optional[float] = None,
    fipe_preco: Optional[float] = None,
    amostra_preco_size: Optional[int] = None,
) -> tuple[float, List[str]]:
    score = 50.0
    insights = []

    score_preco, insights_preco = _score_preco(
        vehicle_data,
        preco_medio_mercado,
        fipe_preco,
        amostra_preco_size,
    )
    score += score_preco
    insights.extend(insights_preco)

    score_km, insights_km = _score_km(vehicle_data)
    score += score_km
    insights.extend(insights_km)

    score_fotos, insights_fotos = _score_fotos(vehicle_data)
    score += score_fotos
    insights.extend(insights_fotos)

    score_descricao, insights_descricao = _score_descricao(vehicle_data)
    score += score_descricao
    insights.extend(insights_descricao)

    score_vendedor, insights_vendedor = _score_vendedor(vehicle_data)
    score += score_vendedor
    insights.extend(insights_vendedor)

    score = max(0.0, min(100.0, score))
    return round(score, 1), insights


def _score_preco(
    vehicle_data: dict,
    preco_medio: Optional[float],
    fipe_preco: Optional[float] = None,
    amostra_preco_size: Optional[int] = None,
) -> tuple[float, List[str]]:
    score = 0.0
    insights = []

    preco = vehicle_data.get("preco")
    ano = vehicle_data.get("ano")
    if not preco or preco <= 0:
        return -5.0, ["Preco nao informado"]

    preco_referencia = fipe_preco if fipe_preco and fipe_preco > 0 else preco_medio
    if _is_suspicious_price(preco, ano, preco_referencia):
        return -22.0, ["Revisar o preco"]

    # FIPE comparison takes priority when available
    if fipe_preco and fipe_preco > 0:
        ratio = preco / fipe_preco
        pct = abs(round((ratio - 1) * 100))
        if ratio < 0.80:
            score += 22.0
            insights.append(f"Preco {pct}% abaixo da tabela FIPE")
        elif ratio < 0.93:
            score += 14.0
            insights.append(f"Preco {pct}% abaixo da tabela FIPE")
        elif ratio < 1.05:
            score += 5.0
            insights.append("Preco dentro da tabela FIPE")
        elif ratio < 1.20:
            score -= 5.0
            insights.append(f"Preco {pct}% acima da tabela FIPE")
        else:
            score -= 15.0
            insights.append(f"Preco {pct}% acima da tabela FIPE")
        return score, insights

    # Fallback: batch market average
    if preco_medio and preco_medio > 0:
        ratio = preco / preco_medio
        amostra_confiavel = (amostra_preco_size or 0) >= 3
        if ratio < 0.75:
            score += 18.0 if amostra_confiavel else 10.0
            insights.append("Preco bem abaixo da referencia desta busca")
        elif ratio < 0.90:
            score += 10.0 if amostra_confiavel else 6.0
            insights.append("Preco abaixo da referencia desta busca")
        elif ratio < 1.05:
            score += 3.0
            insights.append("Preco alinhado com a referencia desta busca")
        elif ratio < 1.20:
            score -= 2.0 if amostra_confiavel else 0.0
            insights.append("Comparar preco com versoes semelhantes")
        else:
            score -= 8.0 if amostra_confiavel else -2.0
            insights.append("Comparar preco com versoes equivalentes")
    else:
        if preco < 20000:
            score += 5.0
        elif preco > 200000:
            score -= 5.0

    return score, insights


def _score_km(vehicle_data: dict) -> tuple[float, List[str]]:
    score = 0.0
    insights = []

    km = vehicle_data.get("km")
    ano = vehicle_data.get("ano")

    if km is None or km < 0:
        return -3.0, ["Quilometragem nao informada"]

    if _is_suspicious_km(km, ano):
        return -18.0, ["Revisar a quilometragem"]

    if km == 0:
        score += 10.0
        insights.append("Veiculo zero km")
        return score, insights

    if ano:
        idade = max(1, date.today().year - ano)
        km_esperado = idade * KM_MEDIA_ANUAL
        ratio = km / km_esperado

        if ratio < 0.40:
            score += 18.0
            insights.append("KM muito baixa para o ano")
        elif ratio < 0.65:
            score += 12.0
            insights.append("KM baixa para o ano")
        elif ratio < 0.90:
            score += 6.0
            insights.append("KM boa para o ano")
        elif ratio < 1.20:
            score += 0.0
        elif ratio < 1.60:
            score -= 8.0
            insights.append("KM elevada para o ano")
        else:
            score -= 15.0
            insights.append("KM muito elevada para o ano")
    else:
        if km < 30000:
            score += 10.0
            insights.append("Quilometragem baixa")
        elif km < 80000:
            score += 4.0
        elif km > 200000:
            score -= 10.0
            insights.append("Quilometragem muito alta")

    return score, insights


def _score_fotos(vehicle_data: dict) -> tuple[float, List[str]]:
    score = 0.0
    insights = []

    fotos = vehicle_data.get("fotos", [])
    num_fotos = len(fotos) if fotos else 0

    if num_fotos == 0:
        score -= 15.0
        insights.append("Sem fotos no anuncio")
    elif num_fotos < 3:
        score -= 8.0
        insights.append("Poucas fotos no anuncio")
    elif num_fotos < 6:
        score += 2.0
    elif num_fotos < 12:
        score += 5.0
    else:
        score += 8.0
        insights.append("Anuncio com muitas fotos")

    return score, insights


def _score_descricao(vehicle_data: dict) -> tuple[float, List[str]]:
    score = 0.0
    insights = []

    descricao = vehicle_data.get("descricao", "") or ""
    descricao_lower = descricao.lower()

    if len(descricao) < 20:
        score -= 10.0
        insights.append("Descricao muito curta ou ausente")
        return score, insights

    if len(descricao) > 200:
        score += 5.0

    suspicious_found = []
    for term in SUSPICIOUS_TERMS:
        if term in descricao_lower:
            suspicious_found.append(term)

    if len(suspicious_found) >= 3:
        score -= 15.0
        insights.append("Descricao com termos suspeitos")
    elif len(suspicious_found) >= 1:
        score -= 5.0
        insights.append("Descricao com possivel urgencia de venda")

    positive_found = sum(1 for term in POSITIVE_TERMS if term in descricao_lower)
    if positive_found >= 3:
        score += 8.0
    elif positive_found >= 1:
        score += 3.0

    upper_count = sum(1 for c in descricao if c.isupper())
    if len(descricao) > 0 and upper_count / len(descricao) > 0.5:
        score -= 5.0
        insights.append("Descricao em caixa alta (possivel spam)")

    return score, insights


def _score_vendedor(vehicle_data: dict) -> tuple[float, List[str]]:
    score = 0.0
    insights = []

    vendedor_tipo = vehicle_data.get("vendedor_tipo", "")

    if vendedor_tipo == "Concessionária":
        score += 5.0
        insights.append("Vendido por concessionaria")
    elif vendedor_tipo == "Loja":
        score += 3.0
    elif vendedor_tipo == "Pessoa Física":
        score += 1.0

    return score, insights


def calcular_score_batch(vehicles: list, calcular_media_por_modelo: bool = True) -> list:
    if calcular_media_por_modelo:
        precos_por_modelo = {}
        for v in vehicles:
            key = f"{v.get('marca', '')}_{v.get('modelo', '')}_{v.get('ano', 0)}"
            if v.get("preco") and v["preco"] > 0:
                if key not in precos_por_modelo:
                    precos_por_modelo[key] = []
                precos_por_modelo[key].append(v["preco"])

        medias = {
            k: sum(v) / len(v)
            for k, v in precos_por_modelo.items()
            if v
        }
        tamanhos_amostra = {k: len(v) for k, v in precos_por_modelo.items() if v}
    else:
        medias = {}
        tamanhos_amostra = {}

    result = []
    for v in vehicles:
        key = f"{v.get('marca', '')}_{v.get('modelo', '')}_{v.get('ano', 0)}"
        preco_medio = medias.get(key)
        score, insights = calcular_score(v, preco_medio, amostra_preco_size=tamanhos_amostra.get(key))
        result.append({**v, "score": score, "insights": insights})

    return result


async def calcular_score_batch_com_fipe(vehicles: list) -> list:
    """
    Like calcular_score_batch but enriches each vehicle with FIPE price.
    Uses batch market average as fallback when FIPE lookup fails.
    FIPE lookups are deduplicated (one call per unique brand/model/year).
    """
    from app.services.fipe_service import get_fipe_price, preload_brands

    # Build unique lookup keys to avoid duplicate API calls
    fipe_cache: dict[str, Optional[float]] = {}
    unique_keys = set()
    for v in vehicles:
        marca = v.get("marca") or ""
        modelo = v.get("modelo") or ""
        ano = v.get("ano") or 0
        if marca and modelo and ano:
            unique_keys.add((marca, modelo, ano))

    # Preload brands list once so parallel lookups find it cached
    await preload_brands()

    # Resolve FIPE prices concurrently (cap at 3 parallel)
    sem = asyncio.Semaphore(3)  # Limit concurrent FIPE requests to avoid 429

    async def lookup(marca, modelo, ano):
        async with sem:
            result = await get_fipe_price(marca, modelo, ano)
            fipe_cache[f"{marca}_{modelo}_{ano}"] = result["preco"] if result else None

    await asyncio.gather(*(lookup(m, mo, a) for m, mo, a in unique_keys))

    # Batch market average as fallback
    precos_por_modelo: dict[str, list] = {}
    for v in vehicles:
        key = f"{v.get('marca', '')}_{v.get('modelo', '')}_{v.get('ano', 0)}"
        if v.get("preco") and v["preco"] > 0:
            precos_por_modelo.setdefault(key, []).append(v["preco"])

    medias = {k: sum(lst) / len(lst) for k, lst in precos_por_modelo.items() if lst}
    tamanhos_amostra = {k: len(lst) for k, lst in precos_por_modelo.items() if lst}

    result = []
    for v in vehicles:
        key = f"{v.get('marca', '')}_{v.get('modelo', '')}_{v.get('ano', 0)}"
        fipe_preco = fipe_cache.get(key)
        preco_medio = medias.get(key)
        score, insights = calcular_score(
            v,
            preco_medio,
            fipe_preco,
            tamanhos_amostra.get(key),
        )
        entry = {**v, "score": score, "insights": insights}
        if fipe_preco:
            entry["fipe_preco"] = fipe_preco
        result.append(entry)

    return result
