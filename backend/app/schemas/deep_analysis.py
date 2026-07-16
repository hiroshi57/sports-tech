"""深掘り分析スキーマ(外販 B#11-17, B#19)。"""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class AbilityItemResponse(BaseModel):
    name: str
    value: float
    basis: str


class DuelResponse(BaseModel):
    attacking_1v1: float
    defending_1v1: float
    pressing: float
    comment: str


class FootednessResponse(BaseModel):
    dominant_foot_skill: float
    weak_foot_skill: float
    balance_pct: float
    comment: str


class SituationalResponse(BaseModel):
    attacking: float
    defending: float
    transition: float
    comment: str


class HeatmapResponse(BaseModel):
    zones: list[list[float]]  # 3x3 自陣→敵陣 × 左/中/右 (%)
    coverage: float
    comment: str


class DecisionResponse(BaseModel):
    scan_frequency: float
    decision_speed: float
    pre_receive_prep: float
    comment: str


class SetPieceResponse(BaseModel):
    aerial_duel: float
    delivery: float
    box_presence: float
    comment: str


class FatigueResponse(BaseModel):
    curve: list[float]  # 0-90分を15分刻み
    endurance_index: float
    comment: str


class DeepAnalysisResponse(BaseModel):
    """深掘り分析一式（Phase 1 は基礎スコアからの導出値）。"""

    athlete_id: uuid.UUID
    abilities: list[AbilityItemResponse]  # B#11
    duel: DuelResponse  # B#12
    footedness: FootednessResponse  # B#13
    situational: SituationalResponse  # B#14
    heatmap: HeatmapResponse  # B#15
    decision: DecisionResponse  # B#16
    set_piece: SetPieceResponse  # B#17
    fatigue: FatigueResponse  # B#19
    method_note: str
    is_reference_score: bool = True
