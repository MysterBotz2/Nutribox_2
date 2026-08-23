from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProfileConsentState(str, Enum):
    NOT_ASKED = "not_asked"
    GRANTED = "granted"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class PregnancyStatus(str, Enum):
    PREGNANT = "pregnant"
    POSTPARTUM = "postpartum"
    NONE = "none"
    DECLINED = "declined"


class PregnancyDurationUnit(str, Enum):
    WEEKS = "weeks"
    MONTHS = "months"


class SmokingStatus(str, Enum):
    NEVER = "never"
    LAST_6_MONTHS = "last_6_months"
    LAST_12_MONTHS = "last_12_months"
    MORE_THAN_12_MONTHS_AGO = "more_than_12_months_ago"


class SmokingMethod(str, Enum):
    CIGARETTES = "cigarettes"
    ALTERNATIVE_TOBACCO = "alternative_tobacco"
    VAPING = "vaping"
    E_CIGARETTES = "e_cigarettes"
    CANNABIS = "cannabis"
    NONE = "none"


class DrinkingStatus(str, Enum):
    NEVER = "never"
    FORMER = "former"
    CURRENT = "current"


class DrinkingFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    OCCASIONALLY = "occasionally"
    RARELY = "rarely"


class DrinkingAverageIntake(str, Enum):
    ONE_TO_TWO = "one_to_two"
    THREE_TO_FOUR = "three_to_four"
    FIVE_OR_MORE = "five_or_more"


class LastAlcoholConsumption(str, Enum):
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    MORE_THAN_30_DAYS_AGO = "more_than_30_days_ago"
    NEVER = "never"


class AlcoholType(str, Enum):
    BEER = "beer"
    WINE = "wine"
    SPIRITS = "spirits"
    MIXED_DRINKS = "mixed_drinks"


class BodyBuild(str, Enum):
    LEAN = "lean"
    AVERAGE = "average"
    MUSCULAR = "muscular"
    STOCKY = "stocky"


class WeightStatus(str, Enum):
    UNDERWEIGHT = "underweight"
    NORMAL_WEIGHT = "normal_weight"
    OVERWEIGHT = "overweight"
    OBESITY = "obesity"


class Ethnicity(str, Enum):
    FILIPINO = "filipino"
    OTHER = "other"
    DECLINED = "declined"


class MedicalNeed(str, Enum):
    DIABETIC_FRIENDLY = "diabetic_friendly"
    LOW_SODIUM = "low_sodium"
    HEART_FRIENDLY = "heart_friendly"
    RENAL_FRIENDLY = "renal_friendly"
    PREGNANCY_FRIENDLY = "pregnancy_friendly"
    GLUTEN_FREE = "gluten_free"
    LACTOSE_FREE = "lactose_free"


class ProfileConsentUpdateRequest(BaseModel):
    """Full replacement of three independent product permission states."""

    model_config = ConfigDict(extra="forbid")

    sensitive_storage: ProfileConsentState
    personalization: ProfileConsentState
    ai_context: ProfileConsentState


class ProfileConsentResponse(ProfileConsentUpdateRequest):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    updated_at: datetime | None


class SensitiveProfileUpdateRequest(BaseModel):
    """Full replacement of active sensitive declarations; null means unknown or cleared."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    medical_conditions: list[str] | None = Field(default=None, max_length=8)
    medical_conditions_other: str | None = Field(default=None, max_length=250)
    pregnancy_status: PregnancyStatus | None = None
    pregnancy_duration_value: int | None = Field(default=None, ge=0, le=1000)
    pregnancy_duration_unit: PregnancyDurationUnit | None = None
    pregnancy_due_date: date | None = None
    smoking_status: SmokingStatus | None = None
    smoking_methods: list[SmokingMethod] | None = Field(default=None, max_length=6)
    drinking_status: DrinkingStatus | None = None
    drinking_frequency: DrinkingFrequency | None = None
    average_alcohol_intake: DrinkingAverageIntake | None = None
    last_alcohol_consumption: LastAlcoholConsumption | None = None
    alcohol_types: list[AlcoholType] | None = Field(default=None, max_length=4)
    body_build: BodyBuild | None = None
    weight_status: WeightStatus | None = None
    ethnicity: Ethnicity | None = None
    medical_needs: list[MedicalNeed] | None = Field(default=None, max_length=7)

    @field_validator("medical_conditions", mode="before")
    @classmethod
    def normalize_medical_conditions(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        normalized: list[str] = []
        for value in values:
            if not isinstance(value, str):
                raise ValueError("Medical conditions must be strings.")
            cleaned = " ".join(value.strip().lower().split())
            if not cleaned:
                raise ValueError("Medical conditions must not contain blank values.")
            if cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @field_validator("smoking_methods", "alcohol_types", mode="before")
    @classmethod
    def normalize_controlled_collections(cls, values):
        if values is None:
            return None
        normalized = []
        for value in values:
            if not isinstance(value, str):
                raise ValueError("Profile selections must be strings.")
            cleaned = value.strip().lower()
            if not cleaned:
                raise ValueError("Profile selections must not contain blank values.")
            if cleaned not in normalized:
                normalized.append(cleaned)
        return normalized

    @field_validator("medical_needs")
    @classmethod
    def medical_needs_must_be_unique(cls, values):
        if values is not None and len(values) != len(set(values)):
            raise ValueError("Profile selections must not contain duplicate values.")
        return values

    @model_validator(mode="after")
    def validate_related_values(self) -> "SensitiveProfileUpdateRequest":
        conditions = set(self.medical_conditions or ())
        if "none" in conditions and len(conditions) != 1:
            raise ValueError("'none' cannot be combined with another medical condition.")
        if self.medical_conditions_other is not None and "other" not in conditions:
            raise ValueError("medical_conditions_other requires medical_conditions to include 'other'.")
        duration_present = self.pregnancy_duration_value is not None or self.pregnancy_duration_unit is not None
        if (self.pregnancy_duration_value is None) != (self.pregnancy_duration_unit is None):
            raise ValueError("Pregnancy duration value and unit must be supplied together.")
        if (duration_present or self.pregnancy_due_date is not None) and self.pregnancy_status != PregnancyStatus.PREGNANT:
            raise ValueError("Pregnancy timing and due date are allowed only when pregnancy_status is 'pregnant'.")
        if self.smoking_status == SmokingStatus.NEVER:
            self.smoking_methods = [SmokingMethod.NONE]
        elif self.smoking_methods is not None and SmokingMethod.NONE in self.smoking_methods:
            if len(self.smoking_methods) != 1:
                raise ValueError("'none' cannot be combined with another smoking method.")
        if self.drinking_status == DrinkingStatus.NEVER:
            self.last_alcohol_consumption = LastAlcoholConsumption.NEVER
            self.drinking_frequency = None
            self.average_alcohol_intake = None
            self.alcohol_types = []
        return self


class SensitiveProfileResponse(SensitiveProfileUpdateRequest):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    created_at: datetime
    updated_at: datetime
