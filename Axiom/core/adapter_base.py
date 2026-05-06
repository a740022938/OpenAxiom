from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict


class DatasetAdapter(ABC):
    @abstractmethod
    def detect(self, path: str | Path) -> Dict[str, Any]:
        raise NotImplementedError


class AnnotationAdapter(ABC):
    @abstractmethod
    def load(self, image_rel: str) -> Any:
        raise NotImplementedError

    @abstractmethod
    def save(self, image_rel: str, data: Any) -> None:
        raise NotImplementedError


class TrainerAdapter(ABC):
    @abstractmethod
    def train(self, config: Dict[str, Any]) -> Any:
        raise NotImplementedError


class PredictorAdapter(ABC):
    @abstractmethod
    def predict(self, input_path: str | Path, config: Dict[str, Any]) -> Any:
        raise NotImplementedError
