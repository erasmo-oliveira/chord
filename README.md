# Laboratório do algoritmo Chord

Resumo do Chord como tabela hash distribuída, na forma da seção 6.2.3 de van Steen e Tanenbaum, *Distributed Systems* 4.01 (o PDF está neste repositório). O código em `src/chord.py` segue a Nota 6.1 e a Figura 6.4 do mesmo capítulo: cada nó recalcula a finger table a partir do conjunto de participantes e responde um passo da busca.

Chord atribui identificadores a nós e chaves e resolve uma chave `k` para o endereço do nó responsável por ela. Nós e chaves compartilham um espaço de `m` bits. No livro, `m` costuma ser 128 ou 160, conforme a função de hash. A Figura 6.2 usa `m = 5`, então os identificadores vão de 0 a 31 e a aritmética é módulo 32.

## Sucessor

A entidade de chave `k` fica com o nó de menor identificador `id` tal que `id ≥ k`, dando a volta no anel se for preciso. Esse nó é o sucessor de `k`, escrito `succ(k)`. Cada nó `p` também guarda o predecessor.

Se cada nó só conhecesse o próximo, `succ(p + 1)`, um pedido percorreria o anel até achar o responsável. Em média, o caminho tem metade do anel. Consultar também o predecessor reduz esse custo pela metade. O caminho ainda cresce junto com o anel.

## Finger table

Cada nó `p` guarda uma finger table com `s ≤ m` entradas:

```text
FT_p[i] = succ(p + 2^(i-1))
```

A entrada `i` aponta para o primeiro nó que está pelo menos `2^(i-1)` posições à frente de `p`. São atalhos para nós que já existem; a distância dobra a cada índice. Com `s = 1`, a busca volta a percorrer o anel de um em um.

Na Figura 6.4, a tabela do código tem duas posições a mais. `FT[0]` é o predecessor. A última posição é o próprio nó, para o teste de intervalo ter com quem comparar depois da última entrada.

## Busca

O nó `p` que recebe a chave `k` aplica a regra da Figura 6.4:

1. Se `k` está em `(predecessor, p]`, `p` é o responsável e devolve o próprio endereço.
2. Se `k` está em `(p, FT_p[1]]`, o sucessor imediato é o responsável.
3. Caso contrário, `p` escolhe a entrada `j` tal que `FT_p[j] ≤ k < FT_p[j+1]` e encaminha o pedido a esse nó.

Os intervalos usam a aritmética do anel: quando o limite inferior passa do superior, o trecho continua do outro lado do zero. `__inbetween` em `src/chord.py` implementa esse teste.

Quem iniciou a busca contacta o nó devolvido e repete. É o esquema iterativo descrito na nota. No esquema recursivo, o nó consultado é quem contactaria o seguinte. O laboratório usa o iterativo: `ChordClient` manda `LOOKUP_REQ` e segue o identificador que volta em `LOOKUP_REP`, até o responsável devolver a si mesmo.

Uma busca leva, em geral, `O(log N)` saltos, com `N` nós no sistema. A Figura 6.3 mostra o tamanho médio do caminho crescendo devagar quando o anel passa de milhares de nós.

## Figura 6.2

O anel da figura tem os nós 1, 4, 9, 11, 14, 18, 20, 21 e 28. As entradas 1 a 5 abaixo são `succ(p + 2^(i-1))`. O predecessor de cada nó é o último da lista circular: o de 1 é 28, o de 4 é 1, e assim por diante.

| Nó | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| 1 | 4 | 4 | 9 | 9 | 18 |
| 4 | 9 | 9 | 9 | 14 | 20 |
| 9 | 11 | 11 | 14 | 18 | 28 |
| 11 | 14 | 14 | 18 | 20 | 28 |
| 14 | 18 | 18 | 18 | 28 | 1 |
| 18 | 20 | 20 | 28 | 28 | 4 |
| 20 | 21 | 28 | 28 | 28 | 4 |
| 21 | 28 | 28 | 28 | 1 | 9 |
| 28 | 1 | 1 | 1 | 4 | 14 |

Chave 26 a partir do nó 1, a linha cheia da figura. `succ(26) = 28`.

| Passo | Nó consultado | Decisão |
| --- | --- | --- |
| 1 | 1 | 26 está em `[FT[5], próximo) = [18, 1)`, segue para 18 |
| 2 | 18 | `FT[2] = 20 ≤ 26 < FT[3] = 28`, segue para 20 |
| 3 | 20 | `21 ≤ 26 < 28`, segue para 21 |
| 4 | 21 | 26 está em `(21, 28]`, segue para o sucessor 28 |
| 5 | 28 | 26 está em `(21, 28]`, o nó 28 é o responsável |

Chave 12 a partir do nó 28, a linha tracejada. `succ(12) = 14`. `ChordClient.run` deixa esses dois valores fixos (`p = 28`, `key = 12`).

| Passo | Nó consultado | Próximo |
| --- | --- | --- |
| 1 | 28 | 4, porque 12 está em `[FT[4], FT[5]) = [4, 14)` |
| 2 | 4 | 9 |
| 3 | 9 | 11 |
| 4 | 11 | 14 |
| 5 | 14 | 14, responsável pela chave |

Trocar o par para `p = 1` e `key = 26` reproduz a linha cheia com a mesma função de um passo.

## Entrada, saída e falha

Um nó `p` que entra pede a um participante qualquer a busca de `succ(p + 1)` e se insere entre o predecessor e o sucessor. Sair retira o nó do anel. Os nós guardam o predecessor para fechar esse elo.

O ponto delicado é manter a finger table. `FT_q[1]` tem de apontar para o próximo nó do anel, `succ(q + 1)`. De tempos em tempos, `q` pergunta `pred(succ(q + 1))`. Se a resposta ainda é `q`, o elo concorda com o sucessor. Se o sucessor já aponta para um `p` com `q < p ≤ succ(q + 1)`, então `p` entrou e `q` faz `FT_q[1] = p`, e confere se `p` registrou `q` como predecessor. As outras entradas se renovam resolvendo `succ(q + 2^(i-1))` em segundo plano.

Se o predecessor deixa de responder, `q` marca `pred(q)` como desconhecido. Quando um nó atualiza o sucessor e encontra esse predecessor desconhecido, avisa o sucessor de que ele é o novo predecessor. Com isso o anel se recompõe depois de falhas e retornos. O detalhe está em Stoica et al., 2003, a referência usada pelo livro.

O `src/chord.py` segue o atalho da Nota 6.1. O conjunto `nodeSet` já vem conhecido, ordenado por identificador. Sempre que a composição do anel muda, o nó ajusta esse conjunto e chama `recomputeFingerTable`.

## Proximidade da rede

A seção fecha com o custo de ignorar a rede física. Um atalho no anel pode cruzar a Internet várias vezes. O livro, citando Castro et al., separa três saídas. Atribuir identificadores pela topologia aproxima no anel quem já está perto, e em um anel de uma dimensão isso concentra falhas correlacionadas. No roteamento por proximidade, cada entrada da finger table guarda `r` candidatos no intervalo `[p + 2^(i-1), p + 2^i - 1]`, e o nó escolhe um que esteja perto e que ainda não ultrapasse a chave. Na seleção de vizinhos por proximidade, quem entra escolhe o vizinho mais próximo quando há alternativas, como no Pastry. No Chord simples há um único sucessor por entrada, então as duas últimas ideias se encontram quando a tabela passa a guardar `r` sucessores.

## Mapa do código

```text
src/chord.py
  ChordNode.__succNode              succ(k) no nodeSet ordenado
  ChordNode.__finger                FT[i] = succ(p + 2^(i-1))
  ChordNode.__recomputeFingerTable  FT[0] = predecessor; última posição = este nó
  ChordNode.__inbetween             k no intervalo, com volta no anel
  ChordNode.__localSuccNode         um passo da busca da Figura 6.4
  ChordNode.run                     LOOKUP_REQ devolve LOOKUP_REP com o próximo nó
  ChordClient.run                   busca iterativa da chave 12 a partir do nó 28
```

`__localSuccNode` devolve um identificador de nó. O cliente é quem decide o próximo contato. `channel` e `constChord` (`LOOKUP_REQ`, `LOOKUP_REP`, `STOP`) fazem o envio entre os processos. A tabela e a regra da busca ficam em `ChordNode`.
