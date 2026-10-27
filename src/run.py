"""Sobe o anel Chord e dispara as buscas do ChordClient.

O anel da Figura 6.2 (van Steen e Tanenbaum) é o padrão. Para um anel
sorteado, mude USAR_FIGURA para False: o segundo argumento passa a ser
o número de nós, o primeiro é o número de bits e o terceiro é quantas
buscas o cliente executa.

    python3 run.py 5 9 1
    python3 run.py 8 32 30
"""

import multiprocessing
import os
import random
import sys
import time

import channel
import chord

FIGURA = [1, 4, 9, 11, 14, 18, 20, 21, 28]
USAR_FIGURA = True


def node(channelID, nodeID, nodeSet, nBits):
    chordNode = chord.ChordNode(channelID, nodeID, nodeSet, nBits)
    chordNode.run()


def client(channelID, clientID, nodeSet, nBits, numOfExp):
    clientNode = chord.ChordClient(channelID, clientID, nodeSet, nBits)
    clientNode.run(numOfExp)


def main(argv):
    os.environ["PYTHONUNBUFFERED"] = "1"
    multiprocessing.set_start_method("spawn")
    if len(argv) != 3:
        sys.exit("uso: python3 run.py <bits> <nos> <buscas>")
    m = int(argv[0])
    n = int(argv[1])
    r = int(argv[2])
    if m < 1 or n < 1 or r < 1:
        sys.exit("bits, nós e buscas precisam ser inteiros positivos")

    if USAR_FIGURA:
        if m != 5:
            sys.exit("o anel da Figura 6.2 usa 5 bits: python3 run.py 5 9 1")
        nodeSet = list(FIGURA)
    else:
        espaco = pow(2, m)
        if n > espaco:
            sys.exit("não cabem %s nós num espaço de %s identificadores" % (n, espaco))
        nodeSet = random.sample(range(espaco), n)
    nodeSet.sort()

    channelID = 1
    clientID = pow(2, m)
    chan = channel.Channel(channelID, True)

    chordClient = multiprocessing.Process(
        target=client, args=(channelID, clientID, list(nodeSet), m, r)
    )
    chordNodeSet = [
        multiprocessing.Process(target=node, args=(channelID, i, list(nodeSet), m))
        for i in nodeSet
    ]
    codigo = 0
    try:
        for chordNode in chordNodeSet:
            chordNode.start()
        chan.wait_for_members(len(nodeSet))
        time.sleep(0.2)
        chordClient.start()
        chordClient.join(timeout=30)
        if chordClient.is_alive():
            print(
                "o cliente não terminou; o nó inicial da busca não respondeu",
                file=sys.stderr,
            )
            codigo = 1
        elif chordClient.exitcode:
            codigo = chordClient.exitcode
        else:
            for chordNode in chordNodeSet:
                chordNode.join(timeout=5)
                if chordNode.is_alive():
                    print("um nó não encerrou depois do STOP", file=sys.stderr)
                    codigo = 1
    finally:
        for proc in [chordClient, *chordNodeSet]:
            if proc.is_alive():
                proc.terminate()
                proc.join()
    if codigo:
        sys.exit(codigo)


if __name__ == "__main__":
    main(sys.argv[1:])
