import argparse
import io
import json
import logging
import os
import pickle
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

from minio import Minio
import numpy as np
import requests
from sklearn.ensemble import IsolationForest
from thefuzz import fuzz


logging.getLogger(__name__).addHandler(logging.NullHandler())


BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MINIO_ENDPOINT = "localhost:9000"
DEFAULT_MINIO_ACCESS_KEY = "admin"
DEFAULT_MINIO_SECRET_KEY = "admin1234"
DEFAULT_MINIO_SECURE = False
DEFAULT_CLEAN_BUCKET = "clean-documents"
DEFAULT_CURATED_BUCKET = "curated-documents"
DEFAULT_CLEAN_PREFIX = "2026/demo/"
DEFAULT_CURATED_PREFIX = "2026/demo/"
DEFAULT_MODEL_PATH = BASE_DIR / "models" / "isolation_forest.pkl"


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
        model_path: Optional[str] = None,
        require_frozen_model: bool = False,
        save_frozen_model: bool = False,
        force_retrain_model: bool = False,
        model_version: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.semantic_threshold = semantic_threshold
        self.request_timeout = request_timeout
        self.max_retries_429 = max_retries_429
        self.retry_delay_seconds = retry_delay_seconds
        self.model_path = Path(model_path).expanduser() if model_path else None
        self.model_version = model_version or (
            self.model_path.name if self.model_path is not None else "runtime"
        )
        self.model_source = "runtime"

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        self.model = self._initialize_model(
            baseline_ttc=baseline_ttc,
            contamination=contamination,
            random_state=random_state,
            require_frozen_model=require_frozen_model,
            save_frozen_model=save_frozen_model,
            force_retrain_model=force_retrain_model,
        )

    @staticmethod
    def _save_model(model: IsolationForest, model_path: Path) -> None:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        with model_path.open("wb") as model_file:
            pickle.dump(model, model_file)

    @staticmethod
    def _load_model(model_path: Path) -> IsolationForest:
        with model_path.open("rb") as model_file:
            model = pickle.load(model_file)
        if not hasattr(model, "predict"):
            raise TypeError("Loaded model does not expose a predict method")
        return model

    def _initialize_model(
        self,
        baseline_ttc: Optional[Iterable[float]],
        contamination: float,
        random_state: int,
        require_frozen_model: bool,
        save_frozen_model: bool,
        force_retrain_model: bool,
    ) -> IsolationForest:
        if self.model_path is not None and self.model_path.exists() and not force_retrain_model:
            loaded_model = self._load_model(self.model_path)
            self.model_source = "frozen_pkl"
            self.logger.info("Loaded frozen model from %s", self.model_path)
            return loaded_model

        if self.model_path is not None and require_frozen_model and not self.model_path.exists():
            raise FileNotFoundError(f"Frozen model not found: {self.model_path}")

        trained_model = IsolationForest(contamination=contamination, random_state=random_state)
        history = self._prepare_history(baseline_ttc, random_state=random_state)
        trained_model.fit(history)
        self.model_source = "runtime_trained"

        if self.model_path is not None and (save_frozen_model or force_retrain_model):
            self._save_model(trained_model, self.model_path)
            self.model_source = "frozen_pkl_generated"
            self.logger.info("Saved frozen model to %s", self.model_path)

        return trained_model

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
    def _first_non_empty(payload: Dict[str, Any], *keys: str) -> Any:
        for key in keys:
            value = payload.get(key)
            if value not in (None, ""):
                return value
        return None

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
            "model": {
                "source": self.model_source,
                "path": str(self.model_path) if self.model_path is not None else None,
                "version": self.model_version,
            },
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

        metadata["document_type"] = self._first_non_empty(payload, "document_type", "type_document")
        vendor_name = self._first_non_empty(payload, "vendor_name", "entreprise", "emetteur")
        metadata["input_vendor_name"] = vendor_name

        siret = self._first_non_empty(payload, "siret")
        ht = self._first_non_empty(payload, "montant_ht", "total_ht")
        ttc = self._first_non_empty(payload, "montant_ttc", "total_ttc")

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
                vendor_name, metadata.get("api_company_name")
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
    target_path = Path(file_path)
    if not target_path.is_absolute() and not target_path.exists():
        target_path = BASE_DIR / target_path

    with target_path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)
    return active_validator.analyze(payload)


def export_frozen_model(
    model_path: str,
    baseline_ttc: Optional[Iterable[float]] = None,
    contamination: float = 0.05,
    random_state: int = 42,
) -> Dict[str, str]:
    validator = DocumentValidator(
        baseline_ttc=baseline_ttc,
        contamination=contamination,
        random_state=random_state,
        model_path=model_path,
        force_retrain_model=True,
    )
    resolved_path = str(Path(model_path).expanduser().resolve())
    return {
        "model_path": resolved_path,
        "model_source": validator.model_source,
    }


def _read_env_bool(env_name: str, default: bool = False) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _build_minio_client() -> Minio:
    endpoint = os.getenv("MINIO_ENDPOINT", DEFAULT_MINIO_ENDPOINT)
    access_key = os.getenv("MINIO_ACCESS_KEY", os.getenv("MINIO_ACCESS", DEFAULT_MINIO_ACCESS_KEY))
    secret_key = os.getenv("MINIO_SECRET_KEY", os.getenv("MINIO_SECRET", DEFAULT_MINIO_SECRET_KEY))
    secure = _read_env_bool("MINIO_SECURE", DEFAULT_MINIO_SECURE)
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def _build_curated_object_name(source_object_name: str, clean_prefix: str, curated_prefix: str) -> str:
    normalized_source = source_object_name.lstrip("/")
    normalized_clean_prefix = clean_prefix.strip("/")
    normalized_curated_prefix = curated_prefix.strip("/")

    suffix = normalized_source
    if normalized_clean_prefix and normalized_source.startswith(f"{normalized_clean_prefix}/"):
        suffix = normalized_source[len(normalized_clean_prefix) + 1 :]

    if normalized_curated_prefix:
        return f"{normalized_curated_prefix}/{suffix}".strip("/")
    return suffix


def analyze_clean_bucket_to_curated(
    validator: DocumentValidator,
    clean_bucket: str = DEFAULT_CLEAN_BUCKET,
    curated_bucket: str = DEFAULT_CURATED_BUCKET,
    clean_prefix: str = DEFAULT_CLEAN_PREFIX,
    curated_prefix: str = DEFAULT_CURATED_PREFIX,
) -> Dict[str, int]:
    client = _build_minio_client()
    logger = logging.getLogger("MinIOPipeline")

    if not client.bucket_exists(clean_bucket):
        raise RuntimeError(f"Clean bucket not found: {clean_bucket}")

    if not client.bucket_exists(curated_bucket):
        client.make_bucket(curated_bucket)
        logger.info("Created missing curated bucket: %s", curated_bucket)

    summary = {"processed": 0, "written": 0, "failed": 0}

    for obj in client.list_objects(clean_bucket, prefix=clean_prefix, recursive=True):
        object_name = obj.object_name
        if not object_name.lower().endswith(".json"):
            continue

        summary["processed"] += 1
        response = None

        try:
            response = client.get_object(clean_bucket, object_name)
            payload = json.loads(response.read().decode("utf-8-sig"))
        except Exception as exc:
            summary["failed"] += 1
            logger.exception("Unable to read/parse JSON from %s: %s", object_name, exc)
            continue
        finally:
            if response is not None:
                response.close()
                response.release_conn()

        try:
            result = validator.analyze(payload)
            curated_object_name = _build_curated_object_name(
                source_object_name=object_name,
                clean_prefix=clean_prefix,
                curated_prefix=curated_prefix,
            )

            curated_payload = {
                "source_bucket": clean_bucket,
                "source_object": object_name,
                "validated_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "validation": result,
            }

            encoded = json.dumps(curated_payload, ensure_ascii=False, indent=2).encode("utf-8")
            client.put_object(
                curated_bucket,
                curated_object_name,
                io.BytesIO(encoded),
                len(encoded),
                content_type="application/json",
            )

            summary["written"] += 1
            logger.info("Processed %s -> %s", object_name, curated_object_name)
        except Exception as exc:
            summary["failed"] += 1
            logger.exception("Unable to analyze/store curated object for %s: %s", object_name, exc)

    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    parser = argparse.ArgumentParser(description="Validate documents locally or from MinIO clean zone.")
    parser.add_argument(
        "--mode",
        choices=["minio", "local"],
        default="minio",
        help="Execution mode. minio reads from clean bucket and writes to curated bucket.",
    )
    parser.add_argument(
        "--clean-bucket",
        default=os.getenv("MINIO_CLEAN_BUCKET", DEFAULT_CLEAN_BUCKET),
        help="MinIO clean bucket name.",
    )
    parser.add_argument(
        "--curated-bucket",
        default=os.getenv("MINIO_CURATED_BUCKET", DEFAULT_CURATED_BUCKET),
        help="MinIO curated bucket name.",
    )
    parser.add_argument(
        "--clean-prefix",
        default=os.getenv("MINIO_CLEAN_PREFIX", DEFAULT_CLEAN_PREFIX),
        help="Prefix to scan in clean bucket.",
    )
    parser.add_argument(
        "--curated-prefix",
        default=os.getenv("MINIO_CURATED_PREFIX", DEFAULT_CURATED_PREFIX),
        help="Prefix used when writing curated objects.",
    )
    parser.add_argument(
        "--model-path",
        default=os.getenv("VALIDATOR_MODEL_PATH", str(DEFAULT_MODEL_PATH)),
        help="Path to a frozen IsolationForest .pkl model.",
    )
    parser.add_argument(
        "--model-version",
        default=os.getenv("VALIDATOR_MODEL_VERSION"),
        help="Optional model version label injected in analysis metadata.",
    )
    parser.add_argument(
        "--require-frozen-model",
        action="store_true",
        help="Fail if the frozen model path does not exist.",
    )
    parser.add_argument(
        "--save-frozen-model",
        action="store_true",
        help="Save a .pkl model if training occurs at runtime.",
    )
    parser.add_argument(
        "--force-retrain-model",
        action="store_true",
        help="Retrain and overwrite the frozen .pkl model at model-path.",
    )
    parser.add_argument(
        "--export-frozen-model",
        action="store_true",
        help="Export a frozen .pkl model then exit.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Local JSON files to validate when --mode local is used.",
    )
    args = parser.parse_args()

    if args.export_frozen_model:
        export_info = export_frozen_model(
            model_path=args.model_path,
            contamination=0.05,
            random_state=42,
        )
        print(json.dumps(export_info, ensure_ascii=False, indent=2))
        sys.exit(0)

    validator = DocumentValidator(
        model_path=args.model_path,
        model_version=args.model_version,
        require_frozen_model=args.require_frozen_model,
        save_frozen_model=args.save_frozen_model,
        force_retrain_model=args.force_retrain_model,
    )

    if args.mode == "minio":
        run_summary = analyze_clean_bucket_to_curated(
            validator=validator,
            clean_bucket=args.clean_bucket,
            curated_bucket=args.curated_bucket,
            clean_prefix=args.clean_prefix,
            curated_prefix=args.curated_prefix,
        )
        print(json.dumps(run_summary, ensure_ascii=False, indent=2))
        sys.exit(1 if run_summary["failed"] else 0)

    default_targets = ["facture_ok.json", "facture_math_error.json", "facture_fake_siret.json"]
    targets = args.targets
    if not targets:
        targets = [
            target
            for target in default_targets
            if Path(target).exists() or (BASE_DIR / target).exists()
        ]
        if not targets:
            targets = default_targets

    for file_path in targets:
        try:
            print(f"\n>>> ANALYSE DU FICHIER : {file_path}")
            result = analyze_file(file_path, validator=validator)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except FileNotFoundError:
            print(f"Erreur : fichier introuvable: {file_path}")