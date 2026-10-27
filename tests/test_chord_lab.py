import subprocess
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import channel  # noqa: E402
import explicar  # noqa: E402

FIGURA = [1, 4, 9, 11, 14, 18, 20, 21, 28]


class TestLogicaChord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.anel = explicar.montar_anel(channelID=2)

    def test_finger_table_da_figura(self):
        esperado = {
            1: [28, 4, 4, 9, 9, 18, 1],
            4: [1, 9, 9, 9, 14, 20, 4],
            9: [4, 11, 11, 14, 18, 28, 9],
            11: [9, 14, 14, 18, 20, 28, 11],
            14: [11, 18, 18, 18, 28, 1, 14],
            18: [14, 20, 20, 28, 28, 4, 18],
            20: [18, 21, 28, 28, 28, 4, 20],
            21: [20, 28, 28, 28, 1, 9, 21],
            28: [21, 1, 1, 1, 4, 14, 28],
        }
        for nodeID, ft in esperado.items():
            self.assertEqual(self.anel[nodeID].FT, ft)

    def test_toda_chave_chega_no_sucessor(self):
        for inicio in FIGURA:
            for key in range(32):
                rota = explicar.buscar(self.anel, inicio, key, mostrar=False)
                responsavel = self.anel[inicio]._ChordNode__succNode(key)
                self.assertEqual(rota[-1], responsavel)
                self.assertEqual(rota[-1], rota[-2])
                self.assertLessEqual(len(rota) - 1, len(FIGURA))

    def test_rotas_do_livro(self):
        self.assertEqual(
            explicar.buscar(self.anel, 28, 12, mostrar=False),
            [28, 4, 9, 11, 14, 14],
        )
        self.assertEqual(
            explicar.buscar(self.anel, 1, 26, mostrar=False),
            [1, 18, 20, 21, 28, 28],
        )

    def test_destino_ausente_falha_na_hora(self):
        canal = channel.Channel(3, True)
        canal.join(1)
        with self.assertRaises(RuntimeError) as ctx:
            canal.sendTo(28, ("1", 12))
        self.assertIn("não entrou no canal", str(ctx.exception))


class TestExecucao(unittest.TestCase):
    def test_run_figura(self):
        concluido = subprocess.run(
            [sys.executable, "run.py", "5", "9", "1"],
            cwd=SRC,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(concluido.returncode, 0, concluido.stderr)
        saida = concluido.stdout
        self.assertIn(">>> 28 :  [21, 1, 1, 1, 4, 14, 28]", saida)
        self.assertIn(
            "Client got answer for 12 from 14 through route [28, 4, 9, 11, 14, 14]",
            saida,
        )
        self.assertEqual(saida.count(">>> "), 9)


if __name__ == "__main__":
    unittest.main()
