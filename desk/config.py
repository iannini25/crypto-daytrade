"""Environment configuration.

Secrets are detected only as booleans. The key and secret strings are never
stored on the config object and never sent by the public client.

Risk floors are one-way: environment variables may make the desk stricter
(smaller risk, earlier kill, higher R:R) and are rejected if they loosen
the playbook.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


class ConfigError(ValueError):
    """Raised when configuration would weaken a hard desk rule."""


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse a .env file. Values are not logged by this function."""
    parsed: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            parsed[key] = value
    return parsed


def merged_environ(path: str | Path = ".env", base: dict[str, str] | None = None) -> dict[str, str]:
    """Process environment wins over the dotenv file."""
    env = dict(os.environ if base is None else base)
    file_path = Path(path)
    if file_path.is_file():
        for key, value in parse_dotenv(file_path.read_text(encoding="utf-8")).items():
            env.setdefault(key, value)
    return env


@dataclass(frozen=True)
class Config:
    base_url: str = "https://api.bybit.com"
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
    paper_equity_usdt: Decimal = Decimal("20")
    brl_per_usdt: Decimal = Decimal("5")
    ledger_path: str = "data/paper_ledger.json"
    fee_rate: Decimal = Decimal("0.001")
    max_risk: Decimal = Decimal("0.01")
    kill_ratio: Decimal = Decimal("0.90")
    min_rr: Decimal = Decimal("2")
    max_positions: int = 1
    api_key_set: bool = False
    api_secret_set: bool = False
    ai_subaccount_set: bool = False
    live_orders_confirm: str = "false"

    def __repr__(self) -> str:
        return (
            "Config("
            f"base_url={self.base_url!r}, symbols={self.symbols!r}, "
            f"paper_equity_usdt={self.paper_equity_usdt}, "
            f"api_key_set={self.api_key_set}, api_secret_set={self.api_secret_set}, "
            f"ai_subaccount_set={self.ai_subaccount_set}, "
            f"live_orders_confirm={self.live_orders_confirm!r})"
        )


def _decimal_env(env: dict[str, str], name: str, default: str) -> Decimal:
    raw = env.get(name, "").strip()
    if not raw:
        return Decimal(default)
    try:
        return Decimal(raw)
    except Exception as exc:  # noqa: BLE001 — surface a config error, not a decimal traceback
        raise ConfigError(f"{name} must be a decimal number") from exc


def load_config(env: dict[str, str] | None = None, dotenv_path: str | Path | None = ".env") -> Config:
    """Load desk settings. `env` bypasses the process environment (tests)."""
    if env is None:
        source = merged_environ(dotenv_path if dotenv_path is not None else ".env")
    else:
        source = env

    fee_rate = _decimal_env(source, "DESK_FEE_RATE", "0.001")
    max_risk = _decimal_env(source, "DESK_MAX_RISK", "0.01")
    kill_ratio = _decimal_env(source, "DESK_KILL_RATIO", "0.90")
    min_rr = _decimal_env(source, "DESK_MIN_RR", "2")
    equity = _decimal_env(source, "DESK_PAPER_EQUITY_USDT", "20")
    brl = _decimal_env(source, "DESK_BRL_PER_USDT", "5")

    if fee_rate < Decimal("0.001"):
        raise ConfigError("DESK_FEE_RATE cannot be below VIP0 0.10% per side")
    if max_risk <= 0 or max_risk > Decimal("0.01"):
        raise ConfigError("DESK_MAX_RISK cannot exceed 1% of equity")
    if kill_ratio < Decimal("0.90") or kill_ratio >= Decimal("1"):
        raise ConfigError("DESK_KILL_RATIO cannot be looser than 0.90 and must be below 1")
    if min_rr < Decimal("2"):
        raise ConfigError("DESK_MIN_RR cannot be below 2 after fees")
    if equity <= 0:
        raise ConfigError("DESK_PAPER_EQUITY_USDT must be positive")
    if brl <= 0:
        raise ConfigError("DESK_BRL_PER_USDT must be positive")

    category = source.get("DESK_CATEGORY", "spot").strip().lower() or "spot"
    if category != "spot":
        raise ConfigError("DESK_CATEGORY must be spot (Brazil Standard Account; no perps or margin)")

    raw_symbols = source.get("DESK_SYMBOLS", "BTCUSDT,ETHUSDT,SOLUSDT")
    symbols = tuple(part.strip().upper() for part in raw_symbols.split(",") if part.strip())
    if not symbols:
        raise ConfigError("DESK_SYMBOLS is empty")
    for symbol in symbols:
        if not symbol.endswith("USDT") or not symbol.isalnum():
            raise ConfigError(f"symbol must be a USDT spot pair, got {symbol}")

    base_url = source.get("BYBIT_BASE_URL", "https://api.bybit.com").strip() or "https://api.bybit.com"
    if not base_url.startswith("https://"):
        raise ConfigError("BYBIT_BASE_URL must be https")

    confirm = source.get("LIVE_ORDERS_CONFIRM", "false").strip() or "false"
    return Config(
        base_url=base_url.rstrip("/"),
        symbols=symbols,
        paper_equity_usdt=equity,
        brl_per_usdt=brl,
        ledger_path=source.get("DESK_LEDGER_PATH", "data/paper_ledger.json").strip()
        or "data/paper_ledger.json",
        fee_rate=fee_rate,
        max_risk=max_risk,
        kill_ratio=kill_ratio,
        min_rr=min_rr,
        max_positions=1,
        api_key_set=bool(source.get("BYBIT_API_KEY", "").strip()),
        api_secret_set=bool(source.get("BYBIT_API_SECRET", "").strip()),
        ai_subaccount_set=bool(source.get("BYBIT_AI_SUBACCOUNT_ID", "").strip()),
        live_orders_confirm=confirm,
    )
