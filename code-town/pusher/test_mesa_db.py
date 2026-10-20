import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pusher"))

import mesa_db  # noqa: E402
from push import find_agent, load_agents  # noqa: E402

PASS_NAMES = [
    "Trader - Chefe",
    "PumpFun Analista",
    "Monitor X",
    "Monitor Trending",
    "Caçador Memecoins",
    "Holders e Carteira",
    "Risco Memecoins",
    "Estatística Memecoins",
    "Estudante Memecoins",
    "Conferência de Dados",
]
CANONICAL = {
    "Trader - Chefe": "Trader Crypto - Chefe",
    "PumpFun Analista": "PumpFun Analista",
    "Monitor X": "Monitor X",
    "Monitor Trending": "Monitor Trending",
    "Caçador Memecoins": "Caçador Memecoins",
    "Holders e Carteira": "Holders e Carteira",
    "Risco Memecoins": "Risco Memecoins",
    "Estatística Memecoins": "Estatística Memecoins",
    "Estudante Memecoins": "Estudante Memecoins",
    "Conferência de Dados": "Conferência de Dados",
}


class MesaDbTest(unittest.TestCase):
    def test_ten_names_resolve_with_and_without_accents(self) -> None:
        agents = load_agents(ROOT / "agents.json")
        folded = [
            "Trader - Chefe",
            "PumpFun Analista",
            "Monitor X",
            "Monitor Trending",
            "Cacador Memecoins",
            "Holders e Carteira",
            "Risco Memecoins",
            "Estatistica Memecoins",
            "Estudante Memecoins",
            "Conferencia de Dados",
        ]
        for passed, plain in zip(PASS_NAMES, folded):
            found = find_agent(agents, passed)
            self.assertIsNotNone(found, passed)
            self.assertEqual(found["name"], CANONICAL[passed])
            self.assertEqual(find_agent(agents, plain)["name"], CANONICAL[passed])
        self.assertIsNone(find_agent(agents, "Monitor"))
        self.assertIsNone(find_agent(agents, "alguém de fora"))

    def test_idle_count_includes_monitor_x_and_trending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["SQLITE_PATH"] = str(Path(tmp) / "mesa.db")
            now = datetime(2026, 10, 20, 2, 0, tzinfo=timezone.utc)
            self.assertEqual(
                mesa_db.log_atividade("Monitor X", "achado", "menções públicas na última hora", "ok"),
                0,
            )
            code = mesa_db.ociosos(now=now + timedelta(minutes=1))
            self.assertEqual(code, 0)
            con = sqlite3.connect(os.environ["SQLITE_PATH"])
            rows = con.execute("SELECT agente FROM atividade").fetchall()
            self.assertEqual(rows, [("Monitor X",)])
            roster = mesa_db.desk_roster(load_agents(ROOT / "agents.json"))
            self.assertEqual([a["name"] for a in roster], list(mesa_db.DESK_NAMES))
            self.assertIn("Monitor X", mesa_db.DESK_NAMES)
            self.assertIn("Monitor Trending", mesa_db.DESK_NAMES)
            self.assertEqual(len(roster), 10)

    def test_cli_rejects_unknown_and_accepts_monitor_trending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "SQLITE_PATH": str(Path(tmp) / "mesa.db")}
            script = str(ROOT / "mesa_db.py")
            bad = subprocess.run(
                [sys.executable, script, "log-atividade", "--agente", "Monitor Z", "--tipo", "achado", "--resumo", "x"],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(bad.returncode, 2)
            self.assertIn("não está na lista", bad.stderr)
            self.assertIn("Monitor X", bad.stderr)
            self.assertIn("Monitor Trending", bad.stderr)
            good = subprocess.run(
                [
                    sys.executable,
                    script,
                    "log-atividade",
                    "--agente",
                    "Monitor Trending",
                    "--tipo",
                    "achado",
                    "--resumo",
                    "trending solana",
                ],
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(good.returncode, 0, good.stderr)
            self.assertIn("ok Monitor Trending", good.stdout)
            listed = subprocess.run([sys.executable, script, "agentes"], env=env, capture_output=True, text=True)
            self.assertEqual(listed.returncode, 0)
            for name in mesa_db.DESK_NAMES:
                self.assertIn(name, listed.stdout)
            idle = subprocess.run([sys.executable, script, "ociosos"], env=env, capture_output=True, text=True)
            self.assertEqual(idle.returncode, 0, idle.stderr)
            self.assertIn("ociosos 9/10", idle.stdout)
            self.assertIn("Monitor X — ocioso — sem registro", idle.stdout)
            self.assertIn("Monitor Trending — trabalhando", idle.stdout)


if __name__ == "__main__":
    unittest.main()
