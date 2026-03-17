import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

import numpy as np
import requests
from sklearn.ensemble import IsolationForest
from thefuzz import fuzz


logging.getLogger(__name__).addHandler(logging.NullHandler())


class DocumentValidator:
    API_URL = "https://recherche-entreprises.api.gouv.fr/search"

    def __init__(
        self,
        baseline_ttc: Optional[Iterable[float]] = None,
        contamination: float = 0.05,
        random_state: int = 42,
        semantic_threshold: int = 80,
        request_timeout: int = 10,
        max_retries_429: int = 2,
        retry_delay_seconds: float = 1.0,
        user_agent: str = "M2-Hackathon-ValidationEngine/1.0",
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.semantic_threshold = semantic_threshold
        self.request_timeout = request_timeout
        self.max_retries_429 = max_retries_429
        self.retry_delay_seconds = retry_delay_seconds

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self.model = IsolationForest(contamination=contamination, random_state=random_state)
        history = self._prepare_history(baseline_ttc, random_state=random_state)
        self.model.fit(history)

    @staticmethod
    def _prepare_history(baseline_ttc: Optional[Iterable[float]], random_state: int) -> np.ndarray:
        cleaned = []
        if baseline_ttc is not None:
            for value in baseline_ttc:
                try:
                    cleaned.append(float(value))
                except (TypeError, ValueError):
                    continue

        if len(cleaned) < 30:
            rng = np.random.default_rng(seed=random_state)
            synthetic = rng.normal(loc=1500.0, scale=220.0, size=200)
            cleaned.extend(float(v) for v in synthetic)

        return np.array(cleaned, dtype=float).reshape(-1, 1)

    @staticmethod
    def _parse_json_payload(json_data: Any) -> Dict[str, Any]:
        if isinstance(json_data, dict):
            return json_data
        if isinstance(json_data, str):
            parsed = json.loads(json_data)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError("JSON payload must be an object")
        raise TypeError("json_data must be a dict or a JSON string")

    @staticmethod
    def _normalize_siret(siret: Any) -> str:
        return "".join(ch for ch in str(siret) if ch.isdigit())

    @staticmethod
    def _extract_result_siret(result: Dict[str, Any]) -> Optional[str]:
        direct = result.get("siret")
        if isinstance(direct, str):
            return "".join(ch for ch in direct if ch.isdigit())

        siege = result.get("siege")
        if isinstance(siege, dict):
            siege_siret = siege.get("siret")
            if isinstance(siege_siret, str):
                return "".join(ch for ch in siege_siret if ch.isdigit())

        return None

    def _validate_siret(self, siret: Any) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        normalized = self._normalize_siret(siret)
        if len(normalized) != 14:
            return False, None, {"error": "SIRET must contain 14 digits", "http_status": None}

        params = {"q": normalized}
        for attempt in range(self.max_retries_429 + 1):
            try:
                response = self.session.get(self.API_URL, params=params, timeout=self.request_timeout)
            except requests.RequestException as exc:
                self.logger.exception("SIRET API request failed for %s", normalized)
                return False, None, {"error": str(exc), "http_status": None}

            if response.status_code == 429:
                if attempt < self.max_retries_429:
                    delay = self.retry_delay_seconds * (attempt + 1)
                    self.logger.warning(
                        "SIRET API rate limited (429) for %s. Retry in %.1fs (%d/%d)",
                        normalized,
                        delay,
                        attempt + 1,
                        self.max_retries_429,
                    )
                    time.sleep(delay)
                    continue
                return False, None, {"error": "API rate limit reached", "http_status": 429}

            if response.status_code >= 400:
                self.logger.error(
                    "SIRET API HTTP error %d for %s", response.status_code, normalized
                )
                return (
                    False,
                    None,
                    {
                        "error": f"HTTP {response.status_code}",
                        "http_status": response.status_code,
                    },
                )

            try:
                payload = response.json()
            except ValueError:
                self.logger.error("SIRET API returned invalid JSON for %s", normalized)
                return False, None, {"error": "Invalid API JSON response", "http_status": 200}

            results = payload.get("results") or []
            if not results:
                return False, None, {"error": "SIRET not found", "http_status": response.status_code}

            selected = results[0]
            for candidate in results:
                if self._extract_result_siret(candidate) == normalized:
                    selected = candidate
                    break

            company_name = selected.get("nom_complet") or selected.get("nom_raison_sociale")
            company_name = str(company_name).strip() if company_name is not None else None

            return (
                True,
                company_name,
                {
                    "http_status": response.status_code,
                    "result_count": len(results),
                },
            )

        return False, None, {"error": "Unexpected retry state", "http_status": None}

    @staticmethod
    def _check_math(ht: Any, ttc: Any) -> bool:
        try:
            ht_value = float(ht)
            ttc_value = float(ttc)
        except (TypeError, ValueError):
            return False
        return abs((ht_value * 1.20) - ttc_value) < 1.0

    def _check_semantic(self, ocr_name: Any, api_name: Optional[str]) -> Tuple[bool, int]:
        if not ocr_name or not api_name:
            return False, 0
        score = fuzz.token_sort_ratio(str(ocr_name).lower(), str(api_name).lower())
        return score >= self.semantic_threshold, int(score)

    def _is_ml_anomaly(self, amount_ttc: Any) -> bool:
        amount = float(amount_ttc)
        prediction = self.model.predict(np.array([[amount]], dtype=float))
        return int(prediction[0]) == -1

    @staticmethod
    def _compute_status(checks: Dict[str, bool]) -> str:
        if checks["siret"] and checks["math"] and checks["ml"]:
            return "VALID"
        if not checks["siret"] or not checks["math"]:
            return "INVALID"
        return "SUSPECT"

    def analyze(self, json_data: Any) -> Dict[str, Any]:
        checks = {"siret": False, "math": False, "ml": False}
        metadata: Dict[str, Any] = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "errors": [],
            "semantic": {"match": False, "score": 0, "threshold": self.semantic_threshold},
            "api": {},
        }
        risk_score = 0

        try:
            payload = self._parse_json_payload(json_data)
        except Exception as exc:
            self.logger.exception("Payload parsing failed")
            metadata["errors"].append(f"payload_error: {exc}")
            return {
                "status": "INVALID",
                "risk_score": 100,
                "checks": checks,
                "metadata": metadata,
            }

        metadata["document_type"] = payload.get("document_type")
        metadata["input_vendor_name"] = payload.get("vendor_name")

        siret = payload.get("siret")
        ht = payload.get("montant_ht")
        ttc = payload.get("montant_ttc")

        try:
            siret_ok, api_name, siret_meta = self._validate_siret(siret)
            checks["siret"] = siret_ok
            metadata["api"] = siret_meta
            metadata["api_company_name"] = api_name
        except Exception as exc:
            self.logger.exception("Unexpected error during SIRET validation")
            checks["siret"] = False
            metadata["errors"].append(f"siret_error: {exc}")

        if not checks["siret"]:
            risk_score += 50
            if isinstance(metadata.get("api"), dict) and metadata["api"].get("error"):
                metadata["errors"].append(f"siret_invalid: {metadata['api']['error']}")
            else:
                metadata["errors"].append("siret_invalid")

        try:
            semantic_ok, semantic_score = self._check_semantic(
                payload.get("vendor_name"), metadata.get("api_company_name")
            )
            metadata["semantic"] = {
                "match": semantic_ok,
                "score": semantic_score,
                "threshold": self.semantic_threshold,
            }
        except Exception as exc:
            self.logger.exception("Unexpected error during semantic matching")
            metadata["errors"].append(f"semantic_error: {exc}")

        try:
            checks["math"] = self._check_math(ht, ttc)
        except Exception as exc:
            self.logger.exception("Unexpected error during arithmetic validation")
            checks["math"] = False
            metadata["errors"].append(f"math_error: {exc}")

        if not checks["math"]:
            risk_score += 30
            metadata["errors"].append("math_invalid")

        try:
            ml_anomaly = self._is_ml_anomaly(ttc)
            checks["ml"] = not ml_anomaly
            metadata["ml_prediction"] = "anomaly" if ml_anomaly else "normal"
        except Exception as exc:
            self.logger.exception("Unexpected error during ML anomaly detection")
            checks["ml"] = False
            metadata["errors"].append(f"ml_error: {exc}")
            ml_anomaly = True

        if ml_anomaly:
            risk_score += 20
            metadata["errors"].append("ml_anomaly")

        risk_score = max(0, min(100, int(risk_score)))
        status = self._compute_status(checks)

        self.logger.info(
            "Document analyzed status=%s risk_score=%d checks=%s",
            status,
            risk_score,
            checks,
        )

        return {
            "status": status,
            "risk_score": risk_score,
            "checks": checks,
            "metadata": metadata,
        }


def analyze_file(file_path: str, validator: Optional[DocumentValidator] = None) -> Dict[str, Any]:
    active_validator = validator or DocumentValidator()
    with open(file_path, "r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    return active_validator.analyze(payload)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    validator = DocumentValidator()
    targets = sys.argv[1:] or ["facture_ok.json", "facture_math_error.json", "facture_fake_siret.json"]

    for file_path in targets:
        try:
            print(f"\n>>> ANALYSE DU FICHIER : {file_path}")
            result = analyze_file(file_path, validator=validator)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except FileNotFoundError:
            print(f"Erreur : fichier introuvable: {file_path}")