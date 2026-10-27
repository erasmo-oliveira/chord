"""Mostra a finger table e a regra usada em cada salto de uma busca.

Usa os métodos de ChordNode, um nó de cada vez, no mesmo processo.
O anel é o da Figura 6.2 e o espaço tem 5 bits.

    python3 explicar.py tabelas
    python3 explicar.py 28 12
    python3 explicar.py 1 26
"""

import sys

import channel
import chord

FIGURA = [1, 4, 9, 11, 14, 18, 20, 21, 28]
BITS = 5


def montar_anel(nodeSet=None, nBits=BITS, channelID=1):
    nos = list(FIGURA if nodeSet is None else nodeSet)
    nos.sort()
    channel.Channel(channelID, True)
    anel = {}
    for nodeID in nos:
        nodo = chord.ChordNode(channelID, nodeID, list(nos), nBits)
        nodo._ChordNode__recomputeFingerTable()
        anel[nodeID] = nodo
    return anel


def justificar(nodo, key):
    ft = nodo.FT
    if nodo._ChordNode__inbetween(key, ft[0] + 1, nodo.nodeID + 1):
        return (
            nodo.nodeID,
            "chave em (predecessor, este] = (%s, %s] → o nó %s é o responsável"
            % (ft[0], nodo.nodeID, nodo.nodeID),
        )
    if nodo._ChordNode__inbetween(key, nodo.nodeID + 1, ft[1]):
        return (
            ft[1],
            "chave em (este, sucessor] = (%s, %s] → o sucessor %s é o responsável"
            % (nodo.nodeID, ft[1], ft[1]),
        )
    for i in range(1, nodo.nBits + 1):
        if nodo._ChordNode__inbetween(key, ft[i], ft[i + 1]):
            return (
                ft[i],
                "chave em [FT[%s], FT[%s]) = [%s, %s) → encaminha para %s"
                % (i, i + 1, ft[i], ft[i + 1], ft[i]),
            )
    return None, "nenhum intervalo da finger table contém a chave"


def buscar(anel, inicio, key, mostrar=True):
    if inicio not in anel:
        raise SystemExit("nó %s não está no anel %s" % (inicio, sorted(anel)))
    nodo = anel[inicio]
    espaco = nodo.MAXPROC
    if key < 0 or key >= espaco:
        raise SystemExit("a chave %s está fora do espaço 0..%s" % (key, espaco - 1))

    def dizer(texto):
        if mostrar:
            print(texto)

    dizer(
        "chave %s a partir do nó %s (succ = %s)"
        % (key, inicio, nodo._ChordNode__succNode(key))
    )
    dizer("rota começa em %s" % inicio)
    atual = inicio
    rota = [atual]
    visto = 0
    while True:
        visto += 1
        if visto > len(anel) + 1:
            raise SystemExit("busca não terminou; rota %s" % rota)
        nodo = anel[atual]
        proximo, texto = justificar(nodo, key)
        conferido = nodo._ChordNode__localSuccNode(key)
        if proximo != conferido:
            raise SystemExit(
                "justificativa (%s) divergiu de __localSuccNode (%s) no nó %s"
                % (proximo, conferido, atual)
            )
        dizer("  nó %s  FT=%s" % (atual, nodo.FT))
        dizer("    %s" % texto)
        rota.append(proximo)
        if proximo == atual:
            break
        atual = proximo
    dizer("responsável: %s" % atual)
    dizer("rota: %s" % rota)
    return rota


def imprimir_tabelas(anel):
    print("FT[0] = predecessor; FT[1..m] = dedos; última posição = o próprio nó")
    for nodeID in sorted(anel):
        nodo = anel[nodeID]
        dedos = "  ".join(
            "FT[%s]=%s" % (i, nodo.FT[i]) for i in range(1, nodo.nBits + 1)
        )
        print(
            "nó %2d  pred=%2d  %s  self=%s"
            % (nodeID, nodo.FT[0], dedos, nodo.FT[-1])
        )


def main(argv):
    if not argv or argv == ["tabelas"]:
        imprimir_tabelas(montar_anel())
        return
    if len(argv) != 2:
        raise SystemExit("uso: python3 explicar.py tabelas | python3 explicar.py <no> <chave>")
    inicio = int(argv[0])
    key = int(argv[1])
    buscar(montar_anel(), inicio, key)


if __name__ == "__main__":
    main(sys.argv[1:])
