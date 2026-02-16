from __future__ import annotations

from typing import Any, Dict, Iterator, List, MutableMapping, Optional, TypeVar, cast

from framework.data.contracts import DataContract, DataEnvelope

T = TypeVar("T", bound=DataContract)


class TypedContext(MutableMapping[str, Any]):
    """
    Type-safe wrapper around execution context.

    - Stores DataContract instances wrapped in DataEnvelope (provenance)
    - Preserves backward compatibility by acting like a dict[str, Any]
      where reading returns raw dict for typed payloads.
    """

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self._data: Dict[str, DataEnvelope[DataContract]] = {}
        self._raw: Dict[str, Any] = dict(initial or {})  # old-style storage

    # ------------------------------------------------------------------
    # Typed API
    # ------------------------------------------------------------------

    def set(
        self,
        key: str,
        value: DataContract,
        actor_name: str,
        *,
        source_step_id: Optional[str] = None,
        source_keys: Optional[List[str]] = None,
    ) -> None:
        """Store typed data with provenance (optionally link to source context keys for lineage)."""
        envelope: DataEnvelope[DataContract] = DataEnvelope(
            payload=value,
            created_by=actor_name,
            source_step_id=source_step_id,
            source_keys=source_keys,
            schema_version=value.schema_version(),
        )
        self._data[key] = envelope
        # Optional: if key existed as raw, remove it to avoid ambiguity
        self._raw.pop(key, None)

    def get(self, key: str, expected_type: type[T]) -> T:  # type: ignore[override]
        """
        Retrieve typed data with validation.

        NOTE: This is a different meaning than dict.get; it is intentionally typed.
        For raw/back-compat use get_raw() or mapping interface.
        """
        envelope = self._data.get(key)
        if envelope is None:
            raise KeyError(f"No typed data for key '{key}'")

        payload = envelope.payload
        if not isinstance(payload, expected_type):
            raise TypeError(
                f"Expected {expected_type.__name__} for key '{key}', got {type(payload).__name__}"
            )
        return cast(T, payload)

    def get_envelope(self, key: str) -> DataEnvelope[DataContract]:
        """If you need provenance (created_by/created_at/source_step_id)."""
        envelope = self._data.get(key)
        if envelope is None:
            raise KeyError(f"No typed data for key '{key}'")
        return envelope

    def get_raw(self, key: str, default: Any = None) -> Any:
        """Backward compatible raw access."""
        if key in self._data:
            return self._data[key].payload.model_dump(mode="json")
        return self._raw.get(key, default)

    def has_typed(self, key: str) -> bool:
        return key in self._data

    # ------------------------------------------------------------------
    # MutableMapping API (dict-like behavior)
    # ------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        # old code doing context["x"] should get raw
        if key in self._data:
            return self._data[key].payload.model_dump(mode="json")
        return self._raw[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Backward compatible: if someone does context["x"] = {...},
        we store in _raw. If they pass a DataContract, we store typed but
        WITHOUT provenance (so we discourage it). Prefer .set(...).
        """
        if isinstance(value, DataContract):
            # store typed, but provenance unknown -> created_by="unknown"
            self.set(key, value, actor_name="unknown")
            return

        self._raw[key] = value
        # if raw overrides a typed key, you may choose to keep typed too.
        # to reduce ambiguity, we remove typed:
        self._data.pop(key, None)

    def __delitem__(self, key: str) -> None:
        removed = False
        if key in self._data:
            del self._data[key]
            removed = True
        if key in self._raw:
            del self._raw[key]
            removed = True
        if not removed:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        # union of keys
        seen = set(self._raw.keys())
        for k in self._data.keys():
            if k not in seen:
                yield k
        for k in self._raw.keys():
            yield k

    def __len__(self) -> int:
        return len(set(self._raw.keys()) | set(self._data.keys()))

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Export a pure dict view (raw compatible).
        Typed payloads are exported as their raw model_dump().
        """
        out: Dict[str, Any] = dict(self._raw)
        for k, env in self._data.items():
            out[k] = env.payload.model_dump(mode="json")
        return out
