"""Offline checks for the public parsers. No network."""

import unittest

from dexscreener import DACITY_MINT, best_quote, pump_mints, trending_quotes
from rugcheck import risk_names, summarize


DACITY = {
    "dexId": "pumpswap",
    "url": "https://dexscreener.com/solana/pair",
    "baseToken": {"address": DACITY_MINT, "name": "Dacity Coin", "symbol": "Dacity"},
    "priceUsd": "0.007127",
    "marketCap": 6997755,
    "liquidity": {"usd": 321425.68},
    "volume": {"h24": 2835712.33},
    "priceChange": {"h24": 108},
}


class ParseTests(unittest.TestCase):
    def test_dacity_fields(self):
        quote = best_quote([DACITY, {**DACITY, "liquidity": {"usd": 1}, "dexId": "pumpfun"}], DACITY_MINT)
        self.assertEqual(quote["priceUsd"], 0.007127)
        self.assertEqual(quote["marketCap"], 6997755)
        self.assertEqual(quote["liquidityUsd"], 321425.68)
        self.assertEqual(quote["volumeH24"], 2835712.33)
        self.assertEqual(quote["changeH24"], 108)
        self.assertEqual(quote["dexId"], "pumpswap")

    def test_trending_is_solana_pump_only(self):
        pump = "Mint1111111111111111111111111111111111pump"
        top = [
            {"chainId": "ethereum", "tokenAddress": "EthMintpump"},
            {"chainId": "solana", "tokenAddress": pump},
            {"chainId": "solana", "tokenAddress": "NotAPumpMint111111111111111111111111111"},
        ]
        self.assertEqual(pump_mints(top), [pump])
        pairs = [{
            "dexId": "pumpfun",
            "baseToken": {"address": pump, "symbol": "POP", "name": "Pop"},
            "priceUsd": "0.2",
            "liquidity": {"usd": 10},
            "volume": {"h24": 3},
            "priceChange": {"h24": 1},
        }]
        rows = trending_quotes(top, [], pairs, 10)
        self.assertEqual([row["symbol"] for row in rows], ["POP"])

    def test_rugcheck_summary_drops_holder_graph(self):
        report = {
            "mint": DACITY_MINT,
            "score": 1,
            "score_normalised": 1,
            "rugged": False,
            "lpLockedPct": 39.6,
            "totalHolders": 1200,
            "risks": [{"name": "Low amount of LP Providers"}],
            "topHolders": [{"address": "secret-looking-but-public", "pct": 4.2}],
        }
        out = summarize(report, DACITY_MINT)
        self.assertEqual(out["risks"], ["Low amount of LP Providers"])
        self.assertNotIn("topHolders", out)
        self.assertEqual(risk_names(report["risks"]), ["Low amount of LP Providers"])
        self.assertFalse(out["rugged"])


if __name__ == "__main__":
    unittest.main()
